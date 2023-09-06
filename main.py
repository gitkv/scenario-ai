import logging
import os
import threading

import yaml
from dacite import from_dict
from dotenv import load_dotenv
from flask import Flask
from pymongo import MongoClient

from models.config import Config
from repos import StoryRepository, TopicRepository
from services.openai import OpenAIApi
from services.story_generator import StoryGenerator
from services.topic_generator import TopicGenerator
from services.voice.base_tts import BaseTTS
from services.voice.silero_tts import SileroTTS
from services.voice.yandex_tts import YandexTTS
from story_controller import StoryController


def load_config(config_name: str) -> Config:
    base_path = os.path.join("config", "base", f"{config_name}.yaml")
    custom_path = os.path.join("config", "custom", f"{config_name}.yaml")

    if os.path.exists(custom_path):
        with open(custom_path, 'r', encoding='utf-8') as file:
            raw_config = yaml.safe_load(file)
    elif os.path.exists(base_path):
        with open(base_path, 'r', encoding='utf-8') as file:
            raw_config = yaml.safe_load(file)
    else:
        raise ValueError(f"No configuration found for {config_name}")

    return from_dict(data_class=Config, data=raw_config)

def initialize_voice_generator(config: Config, yandex_tts_api_key: str) -> BaseTTS:
    if config.voice_generator == "YandexTTS":
        return YandexTTS(yandex_tts_api_key)
    if config.voice_generator == "SileroTTS":
        return SileroTTS(TMP_DIR_BASE)

def create_app(story_repository: StoryRepository) -> Flask:
    story_controller = StoryController(story_repository)
    app = Flask(__name__)
    app.register_blueprint(story_controller.story_routes)
    return app

def main():
    load_dotenv()

    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    config_name = os.getenv("CONFIG_NAME", "default")
    audio_dir = os.path.join("audio", config_name)
    config = load_config(config_name)
    openai_client = OpenAIApi(os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_API_BASE", "https://api.openai.com"))
    voice_generator = initialize_voice_generator(config, os.getenv("YANDEX_TTS_API_KEY"))
    mongo_client = MongoClient('mongodb://username:password@localhost:27017/admin')
    mongo_db = mongo_client[f'{config_name}_scenarios_db']
    topic_repo = TopicRepository(mongo_db['topics'])
    story_repo = StoryRepository(audio_dir, mongo_db['stories'])
    topic_generator = TopicGenerator(config.dialogue_data, int(os.getenv("MAX_SYSTEM_TOPICS", 10)), topic_repo)
    story_generator = StoryGenerator(openai_client, config, voice_generator, audio_dir, int(os.getenv("MAX_SYSTEM_STORIES", 100)), topic_repo, story_repo)

    threading.Thread(target=topic_generator.generate, daemon=True).start()
    threading.Thread(target=story_generator.generate, daemon=True).start()

    app = create_app(story_repo)
    app.run(threaded=True, debug=False, port=5000)

if __name__ == "__main__":
    main()
