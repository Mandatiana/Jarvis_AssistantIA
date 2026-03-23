import time
import os
import json
import shutil
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from faster_whisper import WhisperModel

def find_ffmpeg():
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

def convert_to_wav(src_path, dst_path, timeout=10):
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ffmpeg introuvable dans le PATH.")
        return False
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", src_path,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        dst_path
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if proc.returncode == 0 and os.path.exists(dst_path) and os.path.getsize(dst_path) > 0:
            return True
        print("ffmpeg conversion failed:", proc.stderr[:400])
    except Exception as e:
        print("ffmpeg error:", repr(e))
    return False

def find_ffmpeg():
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

def convert_to_wav(src_path, dst_path, timeout=10):
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ffmpeg introuvable dans le PATH.")
        return False
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", src_path,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        dst_path
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if proc.returncode == 0 and os.path.exists(dst_path) and os.path.getsize(dst_path) > 0:
            return True
        print("ffmpeg conversion failed:", proc.stderr[:400])
    except Exception as e:
        print("ffmpeg error:", repr(e))
    return False

class TranscribeHandler(FileSystemEventHandler):
    def __init__(self, model):
        self.model = model

    def _wait_stable(self, path, stable_checks=3, sleep_interval=0.2, timeout=10):
        last = -1
        stable = 0
        waited = 0.0
        while stable < stable_checks and waited < timeout:
            try:
                cur = os.path.getsize(path)
            except OSError:
                cur = -1
            if cur == last and cur > 0:
                stable += 1
            else:
                stable = 0
            last = cur
            time.sleep(sleep_interval)
            waited += sleep_interval
        return last > 0

    def _wait_stable(self, path, stable_checks=3, sleep_interval=0.2, timeout=10):
        last = -1
        stable = 0
        waited = 0.0
        while stable < stable_checks and waited < timeout:
            try:
                cur = os.path.getsize(path)
            except OSError:
                cur = -1
            if cur == last and cur > 0:
                stable += 1
            else:
                stable = 0
            last = cur
            time.sleep(sleep_interval)
            waited += sleep_interval
        return last > 0

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac', '.aac'):
            return

        print(f"Nouveau fichier détecté : {path}")
        if not self._wait_stable(path):
            print("Fichier non stable ou trop petit, saut.")
            return

        try:
            work_path = path
            # if not wav, convert to wav in a temp file next to source
            if ext != '.wav':
                tmp_wav = os.path.splitext(path)[0] + "_converted.wav"
                ok = convert_to_wav(path, tmp_wav)
                if ok:
                    work_path = tmp_wav
                else:
                    print("Conversion vers WAV échouée, essaye quand même la transcription si possible.")

            print("Début transcription:", work_path)
            segments, info = self.model.transcribe(work_path)
            language = getattr(info, "language", None)
            lang_prob = getattr(info, "language_probability", None)
            print(f"Langue détectée: {language} ({lang_prob})")

            text = "".join([s.text for s in segments]).strip()
            print(f"Transcription: {text[:200]}")

            out_dir = os.path.dirname(path)
            base = os.path.splitext(os.path.basename(path))[0]
            txt_path = os.path.join(out_dir, f"{base}.txt")
            json_path = os.path.join(out_dir, f"{base}.json")

            # write text transcript
            try:
                with open(txt_path, "w", encoding="utf-8") as tf:
                    tf.write(text)
                print("Transcription sauvegardée:", txt_path)
            except Exception as e:
                print("Erreur écriture txt:", repr(e))

            # write metadata + transcript json
            meta = {
                "audio_file": os.path.basename(path),
                "transcript_file": os.path.basename(txt_path),
                "text": text,
                "language": language,
                "language_probability": lang_prob,
                "timestamp": int(time.time())
            }
            try:
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(meta, jf, ensure_ascii=False, indent=2)
                print("Fichier JSON sauvegardé:", json_path)
            except Exception as e:
                print("Erreur écriture json:", repr(e))

            # supprimer le fichier audio original après transcription réussie
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print("Fichier audio original supprimé:", path)
            except Exception as e:
                print("Erreur suppression fichier audio original:", repr(e))

            # cleanup temporary converted wav
            if work_path != path and os.path.exists(work_path):
                try:
                    os.remove(work_path)
                except:
                    pass

        except Exception as e:
            print("Erreur transcription:", repr(e))
        if event.is_directory:
            return
        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac', '.aac'):
            return

        print(f"Nouveau fichier détecté : {path}")
        if not self._wait_stable(path):
            print("Fichier non stable ou trop petit, saut.")
            return

        try:
            work_path = path
            # if not wav, convert to wav in a temp file next to source
            if ext != '.wav':
                tmp_wav = os.path.splitext(path)[0] + "_converted.wav"
                ok = convert_to_wav(path, tmp_wav)
                if ok:
                    work_path = tmp_wav
                else:
                    print("Conversion vers WAV échouée, essaye quand même la transcription si possible.")

            print("Début transcription:", work_path)
            segments, info = self.model.transcribe(work_path)
            language = getattr(info, "language", None)
            lang_prob = getattr(info, "language_probability", None)
            print(f"Langue détectée: {language} ({lang_prob})")

            text = "".join([s.text for s in segments]).strip()
            print(f"Transcription: {text[:200]}")

            out_dir = os.path.dirname(path)
            base = os.path.splitext(os.path.basename(path))[0]
            txt_path = os.path.join(out_dir, f"{base}.txt")
            json_path = os.path.join(out_dir, f"{base}.json")

            # write text transcript
            try:
                with open(txt_path, "w", encoding="utf-8") as tf:
                    tf.write(text)
                print("Transcription sauvegardée:", txt_path)
            except Exception as e:
                print("Erreur écriture txt:", repr(e))

            # write metadata + transcript json
            meta = {
                "audio_file": os.path.basename(path),
                "transcript_file": os.path.basename(txt_path),
                "text": text,
                "language": language,
                "language_probability": lang_prob,
                "timestamp": int(time.time())
            }
            try:
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(meta, jf, ensure_ascii=False, indent=2)
                print("Fichier JSON sauvegardé:", json_path)
            except Exception as e:
                print("Erreur écriture json:", repr(e))

            # supprimer le fichier audio original après transcription réussie
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print("Fichier audio original supprimé:", path)
            except Exception as e:
                print("Erreur suppression fichier audio original:", repr(e))

            # cleanup temporary converted wav
            if work_path != path and os.path.exists(work_path):
                try:
                    os.remove(work_path)
                except:
                    pass

        except Exception as e:
            print("Erreur transcription:", repr(e))

if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PATH_TO_WATCH = os.path.join(CURRENT_DIR, "audio")
    PATH_TO_WATCH = os.path.normpath(PATH_TO_WATCH)
    if not os.path.exists(PATH_TO_WATCH):
        os.makedirs(PATH_TO_WATCH)

    # Charger modèle (une instance)
    try:
        model = WhisperModel("small", device="cpu", compute_type="int8")
        print("Modèle Faster-Whisper chargé.")
    except Exception as e:
        print("Erreur chargement modèle:", repr(e))
        raise

    # Charger modèle (une instance)
    try:
        model = WhisperModel("small", device="cpu", compute_type="int8")
        print("Modèle Faster-Whisper chargé.")
    except Exception as e:
        print("Erreur chargement modèle:", repr(e))
        raise

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
