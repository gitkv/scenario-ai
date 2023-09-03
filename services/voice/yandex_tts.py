import logging
import os
import requests
from .base_tts import BaseTTS
from .translit import Translit

class YandexTTS(BaseTTS):

    SUPPORTED_VOICES = ['jane', 'ermil', 'zahar', 'alyss']

    def __init__(self, api_key):
        super().__init__()
        self.url_base = "https://tts.voicetech.yandex.net/generate?"
        self.api_key = api_key
        self.translit = Translit()

    def generate_voice(self, text: str, voice_id: str, output_dir: str, pos: int):
        super().generate_voice(text, voice_id, output_dir, pos)
        text = self.translit.replace_words_from_dict(text)
        url = f"{self.url_base}format=mp3&lang=ru-RU&key={self.api_key}&emotion=good&speaker={voice_id}&speed=1&text={text}"
        file_path = os.path.join(output_dir, f"{pos}.mp3")
        response = requests.get(url)
        try:
            if response.status_code == 200:
                with open(file_path, "wb") as file:
                    file.write(response.content)
                return pos, file_path
            else:
                logging.error(f"Failed to generate voice for {text} with voice_id {voice_id}. Status code: {response.status_code}")
                return pos, None
        except Exception as e:
            logging.error(f"Error occurred in gen_voice: {e}")
            return pos, file_path
        finally:
            logging.info("Voice Download Finished")
