import os
import json
import base64
import subprocess
import traceback
import time
import uuid
from channels.generic.websocket import WebsocketConsumer
from django.conf import settings

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        try:
            print("ChatConsumer.connect() called")
            audio_dir = os.path.join(settings.BASE_DIR, 'Jarvis', 'services', 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            self.AUDIO_DIR = audio_dir
            self.accept()
            print("ChatConsumer: accepted, AUDIO_DIR=", self.AUDIO_DIR)
        except Exception as e:
            print("ChatConsumer.connect() error:", repr(e))
            traceback.print_exc()
            try: self.close() 
            except: pass

    def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'audio_chunk':
                self.handle_audio_chunk(data)
            elif msg_type == 'recording_complete':
                self.handle_recording_complete(data)
            else:
                self.send(text_data=f"Le server a capté: {text_data}")
        except json.JSONDecodeError:
            self.send(text_data=f"Le server a capté que vous avez dit: {text_data}")

    def handle_audio_chunk(self, data):
        chunk_index = data.get('chunk_index', 0)
        orig_name = data.get('chunk_name', f'audio_chunk_{chunk_index}.webm')
        base64_data = data.get('data', '')

        try:
            # Retirer préfixe data:*;base64, si présent
            if isinstance(base64_data, str) and 'base64,' in base64_data:
                base64_data = base64_data.split('base64,', 1)[1]

            audio_bytes = base64.b64decode(base64_data)

            # assurer extension .webm si aucune extension fournie
            name_root, ext = os.path.splitext(orig_name)
            if not ext:
                ext = '.webm'
                orig_name = f"{name_root}{ext}"

            saved_path = os.path.join(self.AUDIO_DIR, orig_name)
            os.makedirs(os.path.dirname(saved_path), exist_ok=True)

            with open(saved_path, 'wb') as f:
                f.write(audio_bytes)

            print(f"Saved chunk to {saved_path}")

            self.send(text_data=json.dumps({
                'type': 'chunk_received',
                'chunk_index': chunk_index,
                'status': 'success',
                'chunk_name': orig_name,
                'message': f'Chunk {chunk_index} reçu et sauvegardé en {ext.lstrip(".")}'
            }))

        except Exception as e:
            print("handle_audio_chunk error:", repr(e))
            traceback.print_exc()
            self.send(text_data=json.dumps({
                'type': 'chunk_error',
                'error': str(e)
            }))

    def handle_recording_complete(self, data):
        total_chunks = data.get('total_chunks', 0)
        self.send(text_data=json.dumps({
            'type': 'recording_saved',
            'total_chunks': total_chunks,
            'message': f'Enregistrement complet: {total_chunks} chunks'
        }))

    def disconnect(self, close_code):
        pass