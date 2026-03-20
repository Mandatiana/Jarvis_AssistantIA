from faster_whisper import WhisperModel
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
model_size = "small"

# Run on GPU with FP16
model = WhisperModel(model_size, device="cpu", compute_type="int8")
print("Model loaded successfully.")
# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8")

segments, info = model.transcribe("a4.wav", beam_size=5, language="mg")

print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))