import os

from pydub import AudioSegment

from .base_tts import BaseTTS
from .silero.silero_tts_generator import SileroTTSGenerator


class SileroTTS(BaseTTS):

    SUPPORTED_VOICES = ['aidar', 'baya', 'eugene', 'kseniya', 'xenia', 'random']

    def __init__(self):
        super().__init__()
        self.generator = SileroTTSGenerator()

    def convert_wav_to_ogg(self, wav_path, ogg_path):
        audio = AudioSegment.from_wav(wav_path)
        audio.export(ogg_path, format="ogg")
        os.remove(wav_path)

    def generate_voice(self, text: str, voice_id: str, output_dir: str, pos: int):
        super().generate_voice(text, voice_id, output_dir, pos)
        wav_file_path = os.path.join(output_dir, f"{pos}.wav")
        self.generator.generate_audio_file(text, voice_id, wav_file_path)
        ogg_file_path = os.path.splitext(wav_file_path)[0] + ".ogg"
        self.convert_wav_to_ogg(wav_file_path, ogg_file_path)
        return pos, ogg_file_path