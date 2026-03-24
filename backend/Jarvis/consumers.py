import os
import json
import asyncio
import wave
import io
import traceback
import time
import uuid
import shutil
from pathlib import Path
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from .services.tts_service import TTSService


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data):
        await self.send(text_data=f"Le server a capté que vous avez dit: {text_data}")

    async def disconnect(self, close_code):
        pass


class TTSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("tts_user1", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("tts_user1", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self._speak_pipeline(
            data.get("text", ""),
            float(data.get("speed", 1.0)),
            float(data.get("tau", 0.8))
        )

    async def tts_speak(self, event):
        from . import state
        texte = state.derniere_reponse_ia
        if not texte:
            return
        await self._speak_pipeline(texte, event.get("speed", 1.0), event.get("tau", 0.9))

    async def _speak_pipeline(self, text: str, speed: float, tau: float):
        phrases = TTSService.split_phrases(text)
        svc = TTSService.get_instance()
        loop = asyncio.get_event_loop()

        # Génère toutes les phrases en parallèle
        tasks = [
            loop.run_in_executor(
                svc.executor,
                lambda p=phrase: svc.synthesize_to_bytes(p, speed, tau)
            )
            for phrase in phrases
        ]

        # Collecte tous les chunks
        chunks = []
        for task in tasks:
            try:
                audio = await task
                chunks.append(audio)
            except Exception as e:
                await self.send(text_data=json.dumps({
                    "type": "error", "message": str(e)
                }))
                return

        if not chunks:
            return

        # Fusionne tous les WAV en un seul
        output = io.BytesIO()
        with wave.open(output, 'wb') as out_wav:
            for i, chunk in enumerate(chunks):
                with wave.open(io.BytesIO(chunk)) as in_wav:
                    if i == 0:
                        out_wav.setparams(in_wav.getparams())
                    out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))

        output.seek(0)
        await self.send(bytes_data=output.read())
        await self.send(text_data=json.dumps({"type": "done"}))


class AudioRecordingConsumer(AsyncWebsocketConsumer):
    """Consumer optimisé pour l'enregistrement audio avec transcription via FasterWhisper.py"""
    
    POLL_INTERVAL = 0.5  # Réduit de 0.8s à 0.5s
    TRANSCRIPT_TIMEOUT = 60  # Réduit de 120s à 60s (adapté si besoin)
    MAX_FILE_AGE = 3600  # 1h - supprime les anciens fichiers

    async def connect(self):
        """Accepte la connexion WebSocket."""
        try:
            print("🔗 AudioRecordingConsumer connecté")
            self.audio_dir = Path(settings.BASE_DIR) / 'Jarvis' / 'services' / 'audio'
            self.audio_dir.mkdir(parents=True, exist_ok=True)
            
            self.waiting_tasks = []
            self.processed_files = set()  # Cache pour éviter les re-imports
            
            await self.accept()
        except Exception as e:
            print(f" Erreur connect: {repr(e)}")
            await self.close()

    async def disconnect(self, close_code):
        """Annule les tâches en cours."""
        print(f"AudioRecordingConsumer déconnecté (code={close_code})")
        for task in self.waiting_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.waiting_tasks, return_exceptions=True)

    async def receive(self, text_data=None, bytes_data=None):
        """Reçoit et traite les messages/données binaires."""
        try:
            if bytes_data:
                await self._handle_binary_data(bytes_data)
                return
            
            if text_data:
                data = json.loads(text_data)
                if data.get('type') == 'message':
                    await self.send(text_data=f"Echo: {data.get('text', '')}")
        except json.JSONDecodeError as e:
            print(f"⚠ JSON decode error: {repr(e)}")
        except Exception as e:
            print(f"❌ Erreur receive: {repr(e)}")
            traceback.print_exc()

    async def _handle_binary_data(self, bytes_data):
        """Traite les données binaires (enregistrement complet)."""
        try:
            # Parser l'en-tête (4 bytes length + JSON header)
            if len(bytes_data) < 4:
                return
            
            header_len = int.from_bytes(bytes_data[:4], 'little')
            if len(bytes_data) < 4 + header_len:
                return
            
            header_json = bytes_data[4:4+header_len].decode('utf-8')
            header = json.loads(header_json)
            audio_bytes = bytes_data[4+header_len:]
            
            # Sauvegarder le fichier audio
            filename = header.get('filename', f"recording_{int(time.time())}.webm")
            file_path = self.audio_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(audio_bytes)
            
            print(f"💾 Enregistrement sauvegardé: {filename} ({len(audio_bytes)} bytes)")
            
            # Démarrer le polling du transcript (asynchrone)
            base_name = file_path.stem
            task = asyncio.create_task(
                self._poll_transcript(base_name, filename, timeout=self.TRANSCRIPT_TIMEOUT)
            )
            self.waiting_tasks.append(task)
            
        except Exception as e:
            print(f"❌ Erreur traitement binaire: {repr(e)}")
            traceback.print_exc()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Erreur sauvegarde enregistrement'
            }))

    async def _poll_transcript(self, base_name, audio_filename, timeout=60):
        """Polling optimisé — lit les fichiers globaux prompt.txt et text.json"""
        
        # ⚡ Lire les fichiers globaux (pas spécifiques au fichier)
        prompt_path = self.audio_dir / "prompt.txt"
        json_path = self.audio_dir / "text.json"
        
        start_time = time.time()
        last_timestamp = 0  # Tracker le timestamp pour détecter les mises à jour
        
        try:
            while time.time() - start_time < timeout:
                # Vérifier le JSON d'abord (plus complet)
                if json_path.exists():
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        
                        # ⚡ Vérifier si c'est une nouvelle transcription (timestamp différent)
                        current_timestamp = meta.get('timestamp', 0)
                        if current_timestamp > last_timestamp:
                            last_timestamp = current_timestamp
                            
                            await self.send(text_data=json.dumps({
                                'type': 'final_transcript',
                                'audio_file': audio_filename,
                                'text': meta.get('text', ''),
                                'language': meta.get('language', 'fr'),
                                'timestamp': meta.get('timestamp')
                            }))
                            print(f"✅ Transcript reçu: {audio_filename}")
                            self.processed_files.add(base_name)
                            return
                    except json.JSONDecodeError:
                        pass
                
                # Fallback sur le fichier texte
                if prompt_path.exists():
                    try:
                        with open(prompt_path, 'r', encoding='utf-8') as f:
                            text = f.read().strip()
                        
                        if text:  # Seulement si le texte n'est pas vide
                            await self.send(text_data=json.dumps({
                                'type': 'final_transcript',
                                'audio_file': audio_filename,
                                'text': text
                            }))
                            print(f"✅ Transcript reçu (txt): {audio_filename}")
                            self.processed_files.add(base_name)
                            return
                    except Exception:
                        pass
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(self.POLL_INTERVAL)
            
        except asyncio.CancelledError:
            print(f"⏸ Polling annulé pour {base_name}")
            return
        
        # Timeout
        print(f"⏱ Timeout transcription pour {base_name}")
        await self.send(text_data=json.dumps({
            'type': 'transcript_timeout',
            'audio_file': audio_filename,
            'message': 'Transcription non terminée dans le délai imparti'
        }))

# Alias pour compatibilité
ChatConsumer = AudioRecordingConsumer