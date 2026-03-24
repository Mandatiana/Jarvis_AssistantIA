from openvoice import se_extractor
from openvoice.api import ToneColorConverter
import torch, os, shutil
from faster_whisper import WhisperModel
import openvoice.se_extractor as se_mod
 
c = ToneColorConverter('checkpoints_v2/converter/config.json', device='cpu')
c.load_ckpt('checkpoints_v2/converter/checkpoint.pth')
 
def split_cpu(audio_path, target_dir, audio_name):
    model = WhisperModel('base', device='cpu', compute_type='int8')
    os.makedirs(target_dir, exist_ok=True)
    out = os.path.join(target_dir, f'{audio_name}.wav')
    shutil.copy(audio_path, out)
    return target_dir

se_mod.split_audio_whisper = split_cpu

se, _ = se_extractor.get_se('voice_reference/voix.wav', c, vad=False)
torch.save(se, 'voice_reference/voix_se.pth')
print('Embedding regénéré — shape:', se.shape)