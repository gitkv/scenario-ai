import logging
import os

import requests
from pydub import AudioSegment

from .base_tts import BaseTTS
from .translit import Translit


class YandexTTS(BaseTTS):

    SUPPORTED_VOICES = ['jane', 'ermil', 'zahar', 'alyss']

    def __init__(self, api_key):
        super().__init__()
        self.url_base = "https://tts.voicetech.yandex.net/generate?"
        self.api_key = api_key
        self.translit = Translit()

    def convert_mp3_to_ogg(self, mp3_path, ogg_path):
        audio = AudioSegment.from_mp3(mp3_path)
        audio.export(ogg_path, format="ogg")
        os.remove(mp3_path)

    def generate_voice(self, text: str, voice_id: str, output_dir: str, pos: int):
        super().generate_voice(text, voice_id, output_dir, pos)
        text = self.translit.replace_words_from_dict(text)
        url = f"{self.url_base}format=mp3&lang=ru-RU&key={self.api_key}&emotion=good&speaker={voice_id}&speed=1&text={text}"
        mp3_file_path = os.path.join(output_dir, f"{pos}.mp3")
        ogg_file_path = os.path.join(output_dir, f"{pos}.ogg")
        response = requests.get(url)
        try:
            if response.status_code == 200:
                with open(mp3_file_path, "wb") as file:
                    file.write(response.content)
                self.convert_mp3_to_ogg(mp3_file_path, ogg_file_path)
                return pos, ogg_file_path
            else:
                logging.error(f"Failed to generate voice for {text} with voice_id {voice_id}. Status code: {response.status_code}")
                return pos, None
        except Exception as e:
            logging.error(f"Error occurred in gen_voice: {e}")
            return pos, ogg_file_path
        finally:
            logging.info("Voice Download Finished")
