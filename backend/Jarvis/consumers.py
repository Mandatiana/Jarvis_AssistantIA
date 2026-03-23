import os
import json
import asyncio
import wave
import io
import traceback
import time
import uuid
import shutil
import Jarvis.state as state
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
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
        texte = state.derniere_reponse_ia
        if not texte:
           return
        await self._speak_pipeline(texte, event.get("speed", 1.0), event.get("tau", 0.9))

    async def _speak_pipeline(self, text: str, speed: float, tau: float):
        phrases = TTSService.split_phrases(text)
        svc     = TTSService.get_instance()
        loop    = asyncio.get_event_loop()

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

        # Envoie un seul WAV complet
        await self.send(bytes_data=output.read())
        await self.send(text_data=json.dumps({"type": "done"}))



# NOTE: La transcription est maintenant la responsabilité de services/FasterWhisper.py
# Ce consumer sauvegarde les fichiers audio entrants et notifie le frontend
# quand FasterWhisper.py produit les fichiers transcript (.txt / .json).

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Accepte la connexion WebSocket et initialise les variables de session."""
        try:
            print("ChatConsumer.connect() appelé")
            audio_dir = os.path.join(settings.BASE_DIR, 'Jarvis', 'services', 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            self.AUDIO_DIR = audio_dir

            # État de session de transcription en streaming
            self.session_id = None
            self.session_list = None  # fichier contenant la liste des fragments audio
            self.session_out = None   # fichier WAV final concaténé
            self.session_base = None  # nom de base de session
            self.session_active = False
            self.waiter_tasks = []    # suivi des tâches de polling en attente

            # Buffer pour l'enregistrement complet envoyé depuis le frontend (blob brut)
            self.audio_buffer = b""

            await self.accept()
            print("ChatConsumer: connecté, AUDIO_DIR=", self.AUDIO_DIR)
        except Exception as e:
            print("ChatConsumer.connect() erreur:", repr(e))
            traceback.print_exc()
            try: 
                await self.close()
            except: 
                pass

    async def disconnect(self, close_code):
        """Annule les tâches en attente lors de la déconnexion."""
        self.session_active = False
        for task in self.waiter_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.waiter_tasks, return_exceptions=True)
        print(f"ChatConsumer déconnecté, code={close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        """Reçoit et traite les messages du client."""
        try:
            if bytes_data:
                # Message binaire: 4 bytes en-tête length, puis JSON en-tête, puis bytes audio
                try:
                    header_len = int.from_bytes(bytes_data[:4], 'little')
                    header_json = bytes_data[4:4+header_len].decode('utf-8')
                    header = json.loads(header_json)
                except Exception as e:
                    print("Erreur parsing en-tête bytes:", repr(e))
                    return

                audio_bytes = bytes_data[4+header_len:]
                await self.handle_audio_bytes(header, audio_bytes)
                return

            # Message texte JSON
            data = json.loads(text_data) if text_data else {}
            msg_type = data.get('type')

            if msg_type == 'audio_chunk':
                await self.handle_audio_chunk(data)
            elif msg_type == 'recording_complete':
                await self.handle_recording_complete(data)
            else:
                await self.send(text_data=f"Le serveur a capté: {text_data}")
        except json.JSONDecodeError:
            await self.send(text_data=f"Le serveur a capté que vous avez dit: {text_data}")

    def _start_session_if_needed(self):
        """Crée la structure de répertoire de session si nécessaire."""
        if self.session_active:
            return
        self.session_id = str(uuid.uuid4())[:8]
        ts = int(time.time())
        self.session_base = f"recording_{ts}_{self.session_id}"
        self.session_list = os.path.join(self.AUDIO_DIR, f"{self.session_base}_list.txt")
        self.session_out  = os.path.join(self.AUDIO_DIR, f"{self.session_base}.wav")
        # Créer un fichier liste vide
        with open(self.session_list, "w", encoding="utf-8") as f:
            f.write("") 
        self.session_active = True
        print(f"Session démarrée: {self.session_base}")

    async def handle_audio_bytes(self, header, audio_bytes):
        """Traite les données audio binaires (enregistrement complet ou fragments)."""
        try:
            msg_type = header.get('type', 'audio_chunk')

            if msg_type == 'full_recording':
                # Enregistrement complet
                self.audio_buffer += audio_bytes
                temp_name = header.get('filename', f"recording_{int(time.time())}.webm")
                temp_path = os.path.join(self.AUDIO_DIR, temp_name)
                try:
                    with open(temp_path, "wb") as f:
                        f.write(self.audio_buffer)
                    print(f"Enregistrement complet sauvegardé: {temp_path}")
                except Exception as e:
                    print("Erreur écriture enregistrement complet:", repr(e))
                    await self.send(text_data=json.dumps({'type': 'error', 'message': 'Échec sauvegarde enregistrement'}))
                    return

                self.audio_buffer = b""
                base = os.path.splitext(os.path.basename(temp_path))[0]
                # Démarrer la tâche async d'attente du transcript avec 120s de timeout
                task = asyncio.create_task(self._wait_and_forward_transcript(base, temp_path, 120))
                self.waiter_tasks.append(task)
                return

            # Traitement des fragments (mode streaming)
            chunk_index = header.get('chunk_index', 0)
            orig_name = header.get('chunk_name', f'audio_chunk_{chunk_index}.webm')
            name_root, ext = os.path.splitext(orig_name)
            if not ext:
                ext = '.webm'
                orig_name = f"{name_root}{ext}"

            saved_path = os.path.join(self.AUDIO_DIR, orig_name)
            os.makedirs(os.path.dirname(saved_path), exist_ok=True)
            with open(saved_path, 'wb') as f:
                f.write(audio_bytes)
            print(f"Fragment sauvegardé: {saved_path}")

            # Conversion en WAV
            wav_name = f"{name_root}_{chunk_index}.wav"
            wav_path = os.path.join(self.AUDIO_DIR, wav_name)
            converted = await self._try_convert_async(saved_path, wav_path)
            if converted:
                try:
                    os.remove(saved_path)
                except:
                    pass
                saved_file_for_transcription = wav_path
            else:
                saved_file_for_transcription = saved_path

            # Ajouter à la liste de session
            self._start_session_if_needed()
            safe_path = saved_file_for_transcription.replace('\\', '/')
            try:
                with open(self.session_list, "a", encoding="utf-8") as lf:
                    lf.write(f"file '{safe_path}'\n")
            except Exception as e:
                print("Erreur ajout fichier à liste:", repr(e))

            await self.send(text_data=json.dumps({
                'type': 'chunk_received',
                'chunk_index': chunk_index,
                'status': 'success',
                'chunk_name': orig_name,
                'wav_name': os.path.basename(saved_file_for_transcription),
                'message': f'Fragment {chunk_index} reçu'
            }))

        except Exception as e:
            print("Erreur handle_audio_bytes:", repr(e))
            traceback.print_exc()
            await self.send(text_data=json.dumps({'type': 'chunk_error', 'error': str(e)}))

    async def _try_convert_async(self, src, dst, attempts=3, delay=0.3):
        """Convertit l'audio en WAV de manière asynchrone."""
        ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if not ffmpeg_path:
            print("ffmpeg introuvable")
            return False
        try:
            size = os.path.getsize(src)
            if size < 1000:
                print(f"Fichier trop petit ({size} bytes)")
                return False
        except OSError:
            pass

        cmds = [
            [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', dst],
            [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'webm', '-i', src, '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', dst],
        ]
        for attempt in range(attempts):
            for cmd in cmds:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
                    if proc.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
                        return True
                except Exception as e:
                    print(f"Erreur ffmpeg: {repr(e)}")
                await asyncio.sleep(delay)
        return False

    async def handle_recording_complete(self, data):
        """Finalise l'enregistrement en concaténant tous les fragments."""
        total_chunks = data.get('total_chunks', 0)
        try:
            self.session_active = False
            ffmpeg_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
            if ffmpeg_path and os.path.exists(self.session_list):
                cmd = [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error',
                       '-f', 'concat', '-safe', '0', '-i', self.session_list,
                       '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', self.session_out]
                # Exécuter ffmpeg de manière asynchrone
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
                if proc.returncode != 0:
                    print("Échec concaténation ffmpeg:", stderr.decode()[:400])
                else:
                    if not os.path.exists(self.session_out) or os.path.getsize(self.session_out) == 0:
                        print("ffmpeg a produit une sortie vide")

            await self.send(text_data=json.dumps({
                'type': 'recording_saved',
                'total_chunks': total_chunks,
                'message': f'Enregistrement complet: {total_chunks} fragments',
                'session': self.session_base if self.session_base else None,
                'audio_file': os.path.basename(self.session_out)
            }))

            # Démarrer le polling du transcript
            base = os.path.splitext(os.path.basename(self.session_out))[0]
            task = asyncio.create_task(self._wait_and_forward_transcript(base, self.session_out, 120))
            self.waiter_tasks.append(task)
        except Exception as e:
            print("Erreur handle_recording_complete:", repr(e))
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Erreur finalisation'}))

    async def _wait_and_forward_transcript(self, base, audio_path, timeout=30, poll_interval=0.8):
        """Polling asynchrone pour les fichiers transcript produits par FasterWhisper.py."""
        json_path = os.path.join(self.AUDIO_DIR, f"{base}.json")
        txt_path = os.path.join(self.AUDIO_DIR, f"{base}.txt")
        start = time.time()
        try:
            while time.time() - start < timeout:
                try:
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as jf:
                            meta = json.load(jf)
                        text = meta.get("text", "")
                        txt_file = meta.get("transcript_file") or os.path.basename(txt_path)
                        await self.send(text_data=json.dumps({
                            'type': 'final_transcript',
                            'session': base,
                            'text': text,
                            'audio_file': os.path.basename(audio_path),
                            'txt_file': txt_file,
                            'meta': meta
                        }))
                        print(f"Transcript transmis pour {base}")
                        return
                    if os.path.exists(txt_path):
                        with open(txt_path, "r", encoding="utf-8") as tf:
                            text = tf.read()
                        await self.send(text_data=json.dumps({
                            'type': 'final_transcript',
                            'session': base,
                            'text': text,
                            'audio_file': os.path.basename(audio_path),
                            'txt_file': os.path.basename(txt_path)
                        }))
                        print(f"Transcript transmis pour {base}")
                        return
                except Exception as e:
                    print(f"Erreur attente_et_transmision: {repr(e)}")
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            print(f"Tâche polling annulée pour {base}")
            return
        
        # Timeout - informer le client
        try:
            await self.send(text_data=json.dumps({
                'type': 'transcript_timeout',
                'session': base,
                'audio_file': os.path.basename(audio_path),
                'message': 'Aucun transcript trouvé dans le délai imparti'
            }))
        except:
            pass