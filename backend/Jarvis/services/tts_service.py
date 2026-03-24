import io
import os
import re
import tempfile
import hashlib
import torch
import torchaudio
import torchaudio.transforms as T
from gtts import gTTS
from openvoice.api import ToneColorConverter
from concurrent.futures import ThreadPoolExecutor


class TTSService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        print("[TTS] Chargement OpenVoice v2...")
        self.device = "cpu"

        self.converter = ToneColorConverter(
            "checkpoints_v2/converter/config.json",
            device=self.device
        )
        self.converter.load_ckpt("checkpoints_v2/converter/checkpoint.pth")

        self.source_se = torch.load(
            "checkpoints_v2/base_speakers/ses/en-newest.pth",
            map_location=self.device,
            weights_only=True
        )
        self.target_se = torch.load(
            "voice_reference/voix_se.pth",
            map_location=self.device,
            weights_only=True
        )

        self._cache = {}  # cache RAM phrases fréquentes
        self.executor = ThreadPoolExecutor(max_workers=2)

        print(f"[TTS] source_se: {self.source_se.shape}")
        print(f"[TTS] target_se: {self.target_se.shape}")
        print("[TTS] Prêt.")

    @staticmethod
    def split_phrases(text: str) -> list:
        """Découpe le texte en phrases courtes."""
        phrases = re.split(r'(?<=[.!?,;])\s+', text.strip())
        return [p.strip() for p in phrases if p.strip()]

    def _gtts_to_wav_file(self, text: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            # Dans _gtts_to_wav_file
            tts = gTTS(text=text, lang="fr", slow=False)
            tts.save(mp3_path)
            waveform, sr = torchaudio.load(mp3_path)
        finally:
            os.unlink(mp3_path)
        if sr != 22050:
            waveform = T.Resample(sr, 22050)(waveform)
        torchaudio.save(wav_path, waveform, 22050)
        return wav_path

    def synthesize_to_bytes(self, text: str, speed: float = 1.0, tau: float = 0.9) -> bytes:
        # Cache
        key = hashlib.md5(f"{text}{tau}{speed}".encode()).hexdigest()
        if key in self._cache:
            print(f"[TTS] Cache hit : {text[:30]}...")
            return self._cache[key]

        src_path = out_path = None
        try:
            src_path = self._gtts_to_wav_file(text)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out_path = f.name
            self.converter.convert(
                audio_src_path=src_path,
                src_se=self.source_se,
                tgt_se=self.target_se,
                output_path=out_path,
                tau=tau,
                message="@Jarvis"
            )
            with open(out_path, "rb") as f:
                result = f.read()

            # Sauvegarde cache (max 50 entrées)
            if len(self._cache) > 50:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = result
            return result
        finally:
            if src_path and os.path.exists(src_path):
                os.unlink(src_path)
            if out_path and os.path.exists(out_path):
                os.unlink(out_path)