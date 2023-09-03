import os
from .base_tts import BaseTTS
from .silero.silero_tts_generator import SileroTTSGenerator
from pydub import AudioSegment

class SileroTTS(BaseTTS):

    SUPPORTED_VOICES = ['aidar', 'baya', 'eugene', 'kseniya', 'xenia', 'random']

    def __init__(self):
        super().__init__()
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.generator = SileroTTSGenerator(tmp_dir)

    def _run_tts_script(self, voice_id: str, text: str, output_dir: str, pos: int):
        super().generate_voice(text, voice_id, output_dir, pos)
        self.generator.generate_audio_file(text, voice_id, f"{pos}.wav")
        wav_file_path = os.path.join(output_dir, f"{pos}.wav")
        mp3_file_path = os.path.splitext(wav_file_path)[0] + ".mp3"
        sound = AudioSegment.from_wav(wav_file_path)
        sound.export(mp3_file_path, format="mp3")
        os.remove(wav_file_path)

        return pos, mp3_file_path

    def generate_voice(self, text, voice_id, pos):
        super().generate_voice(text, voice_id, pos)
        return self._run_tts_script(voice_id, text, pos)
