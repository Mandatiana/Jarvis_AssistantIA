import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faster_whisper import WhisperModel

class TranscribeHandler(FileSystemEventHandler):
    def __init__(self, model):
        self.model = model

    def on_created(self, event):
        # On vérifie que c'est un fichier audio
        if not event.is_directory and event.src_path.lower().endswith(('.mp3', '.wav', '.m4a')):
            print(f"Nouveau fichier détecté : {event.src_path}")
            time.sleep(0.01)
            
            # Transcription
            segments, info = self.model.transcribe(event.src_path)
            print(f"Langue '{info.language}' détectée ({info.language_probability:.2f})")
            
            text = "".join([s.text for s in segments])
            print(f"Transcription terminée : {text[:50]}...")
            
            # Exemple : Sauvegarder dans un fichier .txt au même endroit
            with open(f"{event.src_path}.txt", "w", encoding="utf-8") as f:
                f.write(text)

if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PATH_TO_WATCH = os.path.join(CURRENT_DIR, "audio")
    PATH_TO_WATCH = os.path.normpath(PATH_TO_WATCH)
    if not os.path.exists(PATH_TO_WATCH):
        os.makedirs(PATH_TO_WATCH)

    model = WhisperModel("small", device="cpu", compute_type="int8")
    print("Chargement du modèle Faster-Whisper terminé.")
    
    event_handler = TranscribeHandler(model)
    observer = Observer()
    observer.schedule(event_handler, PATH_TO_WATCH, recursive=False)
    
    print(f"Surveillance active sur : {PATH_TO_WATCH}")
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt du script...")
        observer.stop()
    observer.join()
