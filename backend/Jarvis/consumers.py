import json
import asyncio
import wave
import io
import Jarvis.state as state
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
