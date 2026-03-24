import time
import os
import json
import shutil
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faster_whisper import WhisperModel


def find_ffmpeg():
    """Trouve le chemin vers ffmpeg."""
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


def convert_to_wav(src_path, dst_path, timeout=10):
    """Convertit un fichier audio en WAV 16kHz mono."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("⚠ ffmpeg introuvable dans le PATH.")
        return False
    
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", src_path,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        dst_path
    ]
    
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            text=True, timeout=timeout)
        if proc.returncode == 0 and os.path.exists(dst_path) and os.path.getsize(dst_path) > 1024:
            return True
        print(f"⚠ ffmpeg conversion failed: {proc.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"⚠ ffmpeg timeout après {timeout}s")
    except Exception as e:
        print(f"⚠ ffmpeg error: {repr(e)}")
    
    return False


class TranscribeHandler(FileSystemEventHandler):
    """Surveille un répertoire et transcrit automatiquement les fichiers audio."""
    
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac', '.aac'}
    STABLE_SIZE_CHECKS = 3
    STABLE_CHECK_INTERVAL = 0.2
    STABLE_TIMEOUT = 15
    PROCESSING_TIMEOUT = 60
    
    # ⚡ NOUVEAU: Fichiers globaux à écraser
    PROMPT_FILE = "prompt.txt"
    TEXT_FILE = "text.json"

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.processing = set()  # Évite les doublons de traitement
        self.audio_dir = None

    def _is_file_stable(self, path):
        """Vérifie que le fichier est complètement écrit."""
        last_size = -1
        stable_count = 0
        waited = 0.0
        
        while stable_count < self.STABLE_SIZE_CHECKS and waited < self.STABLE_TIMEOUT:
            try:
                current_size = os.path.getsize(path)
            except OSError:
                return False
            
            if current_size == last_size and current_size > 1024:
                stable_count += 1
            else:
                stable_count = 0
            
            last_size = current_size
            time.sleep(self.STABLE_CHECK_INTERVAL)
            waited += self.STABLE_CHECK_INTERVAL
        
        return last_size > 1024

    def on_created(self, event):
        """Déclenché quand un fichier est créé."""
        if event.is_directory:
            return
        
        path = event.src_path
        ext = Path(path).suffix.lower()
        
        # Filtrer les formats non supportés
        if ext not in self.SUPPORTED_FORMATS:
            return
        
        # Éviter les doublons
        if path in self.processing:
            return
        
        print(f"📁 Fichier détecté: {Path(path).name}")
        
        # Attendre que le fichier soit complètement écrit
        if not self._is_file_stable(path):
            print(f"⚠ Fichier non stable ou trop petit, saut.")
            return
        
        self.processing.add(path)
        try:
            self._transcribe_file(path)
        finally:
            self.processing.discard(path)

    def _transcribe_file(self, path):
        """Transcrit un fichier audio (avec conversion si nécessaire)."""
        ext = Path(path).suffix.lower()
        work_path = path
        temp_wav = None
        
        try:
            # Conversion rapide si nécessaire
            if ext != '.wav':
                temp_wav = str(Path(path).parent / f"{Path(path).stem}_temp.wav")
                print(f"🔄 Conversion {ext} → WAV...")
                if not convert_to_wav(path, temp_wav, timeout=15):
                    print(f"⚠ Conversion échouée, tentative directe...")
                else:
                    work_path = temp_wav
            
            # Transcription optimisée
            print(f"🎤 Transcription en cours...")
            start_time = time.time()
            
            segments, info = self.model.transcribe(work_path, language="fr")
            
            # Extraire le texte de façon efficace
            text = " ".join(segment.text.strip() for segment in segments).strip()
            elapsed = time.time() - start_time
            
            print(f"✅ Transcription terminée ({elapsed:.2f}s)")
            print(f"📝 Texte: {text[:150]}...")
            
            # ⚡ NOUVEAU: Écraser les fichiers globaux
            self._save_global_results(path, text, info)
            
            # Supprimer le fichier source
            self._cleanup_files(path, temp_wav)
            
        except Exception as e:
            print(f"❌ Erreur transcription: {repr(e)}")
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except:
                    pass

    def _save_global_results(self, original_path, text, info):
        """⚡ NOUVEAU: Écraser les fichiers globaux prompt.txt et text.json"""
        if not self.audio_dir:
            self.audio_dir = os.path.dirname(original_path)
        
        prompt_path = os.path.join(self.audio_dir, self.PROMPT_FILE)
        text_path = os.path.join(self.audio_dir, self.TEXT_FILE)
        
        # ⚡ ÉCRASER prompt.txt (texte brut)
        try:
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"💾 {self.PROMPT_FILE} écrasé ({len(text)} caractères)")
        except Exception as e:
            print(f"⚠ Erreur écriture {self.PROMPT_FILE}: {repr(e)}")
            return
        
        # ⚡ ÉCRASER text.json (métadonnées)
        metadata = {
            "audio_file": Path(original_path).name,
            "text": text,
            "language": getattr(info, "language", "fr"),
            "language_probability": float(getattr(info, "language_probability", 0.0)),
            "timestamp": int(time.time()),
            "duration_seconds": round(time.time() - int(time.time()), 2)
        }
        
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            print(f"💾 {self.TEXT_FILE} écrasé")
        except Exception as e:
            print(f"⚠ Erreur écriture {self.TEXT_FILE}: {repr(e)}")

    def _cleanup_files(self, original_path, temp_wav):
        """Supprime les fichiers temporaires et originaux."""
        # Supprimer le fichier source
        try:
            if os.path.exists(original_path):
                os.remove(original_path)
                print(f"🗑 Fichier source supprimé: {Path(original_path).name}")
        except Exception as e:
            print(f"⚠ Erreur suppression source: {repr(e)}")
        
        # Supprimer le WAV temporaire
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception as e:
                print(f"⚠ Erreur suppression temp: {repr(e)}")


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PATH_TO_WATCH = os.path.normpath(os.path.join(CURRENT_DIR, "audio"))
    
    # Créer le répertoire s'il n'existe pas
    os.makedirs(PATH_TO_WATCH, exist_ok=True)
    
    # Charger le modèle une seule fois
    try:
        print("⏳ Chargement du modèle Faster-Whisper...")
        model = WhisperModel("small", device="cpu", compute_type="int8")
        print("✅ Modèle chargé avec succès")
    except Exception as e:
        print(f"❌ Erreur chargement modèle: {repr(e)}")
        raise
    
    # Démarrer la surveillance
    event_handler = TranscribeHandler(model)
    observer = Observer()
    observer.schedule(event_handler, PATH_TO_WATCH, recursive=False)
    
    print(f"👁 Surveillance active: {PATH_TO_WATCH}\n")
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹ Arrêt du service...")
        observer.stop()
    
    observer.join()
