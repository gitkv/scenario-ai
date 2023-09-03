import logging
import os
import threading

import yaml
from dacite import from_dict
from dotenv import load_dotenv
from flask import Flask, jsonify, send_file
from pymongo import MongoClient

from models.config import Config
from repos import StoryRepository, TopicRepository
from services.story_generator import StoryGenerator
from services.topic_generator import TopicGenerator
from services.voice.base_tts import BaseTTS
from services.voice.silero_tts import SileroTTS
from services.voice.yandex_tts import YandexTTS

app = Flask(__name__)

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

CONFIG_NAME = os.getenv("CONFIG_NAME", "default")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com")
YANDEX_TTS_API_KEY = os.getenv("YANDEX_TTS_API_KEY")
MAX_SCRNARIOS = os.getenv("MAX_SCRNARIOS", 50)

AUDIO_DIR_BASE="audio"

AUDIO_DIR = os.path.join(AUDIO_DIR_BASE, CONFIG_NAME)

os.makedirs(AUDIO_DIR, exist_ok=True)

def load_config(config_name) -> Config:
    base_path = os.path.join("config", "base", f"{config_name}.yaml")
    custom_path = os.path.join("config", "custom", f"{config_name}.yaml")

    if os.path.exists(custom_path):
        with open(custom_path, 'r') as file:
            raw_config = yaml.safe_load(file)
    elif os.path.exists(base_path):
        with open(base_path, 'r') as file:
            raw_config = yaml.safe_load(file)
    else:
        raise ValueError(f"No configuration found for {config_name}")

    return from_dict(data_class=Config, data=raw_config)

def initialize_voice_generator(config: Config) -> BaseTTS:
    if config.voice_generator == "YandexTTS":
        return YandexTTS(YANDEX_TTS_API_KEY)
    if config.voice_generator == "SileroTTS":
        return SileroTTS(TMP_DIR_BASE)

CONFIG = load_config(CONFIG_NAME)
VOICE_GENERATOR = initialize_voice_generator(CONFIG)

logging.info(f"Script started. Config name: {CONFIG_NAME}, voice generator: {CONFIG.voice_generator}, gpt base url: {OPENAI_API_BASE}")

@app.route("/scenarios", methods=["GET"])
def get_scenarios():
    scenarios = []
    for scenario_dir in os.listdir(SCRNARIO_DIR):
        scenario_path = os.path.join(SCRNARIO_DIR, scenario_dir)
        audio_file_path = os.path.join(scenario_path, "output.mp3")
        script_file_path = os.path.join(scenario_path, "script.txt")
        if os.path.exists(audio_file_path) and os.path.exists(script_file_path):
            scenarios.append(int(scenario_dir))
    return jsonify(scenarios)

@app.route("/audio/<int:scenario_number>", methods=["GET"])
def audio(scenario_number):
    audio_file_path = os.path.join(SCRNARIO_DIR, str(scenario_number), "output.mp3")
    if not os.path.exists(audio_file_path):
        return "Error", 404
    return send_file(audio_file_path)

@app.route("/script/<int:scenario_number>", methods=["GET"])
def script(scenario_number):
    script_file_path = os.path.join(SCRNARIO_DIR, str(scenario_number), "script.txt")
    if not os.path.exists(script_file_path):
        return "Error", 404
    return send_file(script_file_path)

@app.route("/delete/<int:scenario_number>", methods=["DELETE"])
def delete_scenario(scenario_number):
    scenario_dir = os.path.join(SCRNARIO_DIR, str(scenario_number))
    try:
        for filename in os.listdir(scenario_dir):
            os.remove(os.path.join(scenario_dir, filename))
        os.rmdir(scenario_dir)
        return "Deleted", 200
    except Exception as e:
        return f"Failed to delete scenario {scenario_number}: {e}", 500

client = MongoClient('mongodb://username:password@localhost:27017/')
db = client[f'{CONFIG_NAME}_scenarios_db']
totic_collection = db['topics']
story_collection = db['stories']
topic_repo = TopicRepository(totic_collection)
story_repo = StoryRepository(story_collection)

topic_generator = TopicGenerator(CONFIG.dialogue_data, topic_repo)
story_generator = StoryGenerator(OPENAI_API_KEY, OPENAI_API_BASE, CONFIG, VOICE_GENERATOR, AUDIO_DIR, MAX_SCRNARIOS, topic_repo, story_repo)


if __name__ == "__main__":
    threading.Thread(target=topic_generator.generate, daemon=True).start()
    threading.Thread(target=story_generator.generate, daemon=True).start()
    app.run(threaded=True, debug=False, port=5000)
