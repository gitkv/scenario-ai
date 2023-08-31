import logging
import os
import requests
from .base_tts import BaseTTS
from .translit import Translit

class YandexTTS(BaseTTS):

    SUPPORTED_VOICES = ['jane', 'ermil', 'zahar', 'alyss']

    def __init__(self, tmp_dir, api_key):
        super().__init__()
        self.url_base = "https://tts.voicetech.yandex.net/generate?"
        self.tmp_dir = tmp_dir
        self.api_key = api_key
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.translit = Translit()

    def generate_voice(self, text, voice_id, pos):
        super().generate_voice(text, voice_id, pos)
        text = self.translit.replace_words_from_dict(text)
        url = f"{self.url_base}format=mp3&lang=ru-RU&key={self.api_key}&emotion=good&speaker={voice_id}&speed=1&text={text}"
        response = requests.get(url)
        try:
            if response.status_code == 200:
                file_path = os.path.join(self.tmp_dir, f"speech{pos}.mp3")
                with open(file_path, "wb") as file:
                    file.write(response.content)
                return pos, file_path
            else:
                logging.error(f"Failed to generate voice for {text} with voice_id {voice_id}. Status code: {response.status_code}")
                return pos, None
        except Exception as e:
            logging.error(f"Error occurred in gen_voice: {e}")
            return pos, f"{self.tmp_dir}/speech{pos}.mp3"
        finally:
            logging.info("Voice Download Finished")
