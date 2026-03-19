import time
from django.core.management.base import BaseCommand
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faster_whisper import WhisperModel
from faster_whisper import WhisperModel
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


class TranscribeHandler(FileSystemEventHandler):
    def __init__(self, model):
        self.model = model

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.mp3', '.wav', '.m4a')):
            print(f"Nouveau fichier détecté : {event.src_path}")
            segments, info = self.model.transcribe(event.src_path)
            print("Langue '%s' détéctée avec probqbilité %f" % (info.language, info.language_probability))
            text = "".join([s.text for s in segments])
            print(f"Transcription terminée : {text[:50]}...")
            # Ici tu peux créer/modifier un objet Django Model avec le résultat

class Command(BaseCommand):
    help = "Lance le moteur Faster-Whisper en mode surveillance de dossier"

    def handle(self, *args, **options):
        self.stdout.write("Chargement du modèle Faster-Whisper...")
        model = WhisperModel("small", device="cpu", compute_type="int8")
        
        path = "./media/uploads_to_process" # Dossier à surveiller
        event_handler = TranscribeHandler(model)
        observer = Observer()
        observer.schedule(event_handler, path, recursive=False)
        
        self.stdout.write(self.style.SUCCESS(f"Surveillance active sur : {path}"))
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
