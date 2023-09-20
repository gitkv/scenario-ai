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
from services.donation_alerts_parser_service import DonationAlertsParserService
from services.donation_alerts_service import DonationAlertsService
from services.openai import OpenAIApi
from services.rss_news_service import RSSNewsService
from services.story_generator import StoryGenerator
from services.telegram_service import TelegramService
from services.text_filter.text_filter import TextFilter
from services.topic_generator import TopicGenerator
from services.voice.base_tts import BaseTTS
from services.voice.silero_tts import SileroTTS
from services.voice.yandex_tts import YandexTTS
from story_controller import StoryController

def setup_logging():
    # Основная настройка логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Обработчик для вывода логов уровня INFO в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Обработчик для записи логов уровня ERROR в файл
    file_handler = logging.FileHandler("error_logs.log")
    file_handler.setLevel(logging.ERROR)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

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
        return SileroTTS()

def create_app(story_repository: StoryRepository) -> Flask:
    story_controller = StoryController(story_repository)
    app = Flask(__name__)
    app.register_blueprint(story_controller.story_routes)
    return app

def run_flask_app(story_repo):
    app = create_app(story_repo)
    app.run(threaded=True, debug=False, port=5000)

def main():
    setup_logging()

    load_dotenv()

    with open("banned_words.txt", "r", encoding="utf-8") as file:
        banned_words = file.readlines()

    config_name = os.getenv("CONFIG_NAME", "default")
    da_alert_service_variant = os.getenv("DA_ALERT_SERVICE_VARIANT", "websocket")
    audio_dir = os.path.join("audio", config_name)
    config = load_config(config_name)
    openai_client = OpenAIApi(os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_API_BASE", "https://api.openai.com"))
    voice_generator = initialize_voice_generator(config, os.getenv("YANDEX_TTS_API_KEY"))
    mongo_client = MongoClient(os.getenv("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017/"))
    mongo_db = mongo_client[f'{config_name}_scenarios_db']
    topic_repo = TopicRepository(mongo_db['topics'])
    story_repo = StoryRepository(audio_dir, mongo_db['stories'])
    text_filter = TextFilter(banned_words)
    topic_generator = TopicGenerator(config.dialogue_data, int(os.getenv("MAX_SYSTEM_TOPICS", 5)), topic_repo)
    rss_news_service = RSSNewsService(text_filter, config.rss_urls, topic_repo, int(os.getenv("MAX_RSS_TOPICS", 20)))
    telegram_service = TelegramService(os.getenv("TELEGRAM_TOKEN"), text_filter, topic_repo, os.getenv("TELEGRAM_MODERATOR_ID"), os.getenv("DONAT_URL"))
    story_generator = StoryGenerator(openai_client, config, voice_generator, audio_dir, int(os.getenv("MAX_SYSTEM_STORIES", 10)), int(os.getenv("MAX_RSS_STORIES", 100)), topic_repo, story_repo)

    threading.Thread(target=topic_generator.generate, daemon=True).start()
    threading.Thread(target=story_generator.generate, daemon=True).start()
    threading.Thread(target=rss_news_service.run, daemon=True).start()
    threading.Thread(target=run_flask_app, args=(story_repo,)).start()

    if(da_alert_service_variant == 'websocket'):
        donation_alerts_service = DonationAlertsService(os.getenv("DA_ALERT_WIDGET_TOKEN"), topic_repo)
    else:
        donation_alerts_service = DonationAlertsParserService(os.getenv("DA_ALERT_WIDGET_TOKEN"), topic_repo)

    threading.Thread(target=donation_alerts_service.start, daemon=True).start()

    telegram_service.run()

if __name__ == "__main__":
    main()
