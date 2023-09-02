import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore

from pydub import AudioSegment
from pydub.utils import mediainfo

from models.config import Config
from services.openai import OpenAIApi, OpenAIApiException
from services.theme_generator import generate_theme
from services.voice.base_tts import BaseTTS


class SceneGenerator:
    def __init__(self, openai_api_key: str, openai_api_base: str, config: Config, voice_generator: BaseTTS, tmp_dir: str, scenarios_dir: str, max_scenarios: int):
        self.config = config
        self.tmp_dir = tmp_dir
        self.scenarios_dir = scenarios_dir
        self.openai_api = OpenAIApi(openai_api_key, openai_api_base)
        self.voice_generator = voice_generator
        self.max_scenarios = max_scenarios

        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

        if not os.path.exists(self.scenarios_dir):
            os.makedirs(self.scenarios_dir)

    def generate(self):
        while True:
            if self.count_scenarios() >= self.max_scenarios:
                logging.info(f"Reached the maximum number of scenarios ({self.max_scenarios}). Pausing generation.")
                time.sleep(10)
                continue
            
            try:
                logging.info("Generation Started")
                self.validate_all_scenario_directories()

                increment = self.get_increment()
                output_dir = self.create_output_directory(increment)
                theme = self.get_next_theme()

                if not theme:
                    raise ValueError("Empty theme")

                scenario = self.generate_scenario(theme)
                
                self.validate_scenario(scenario)

                audio_files = self.generate_audio_files(scenario)
                time.sleep(1)
                self.validate_audio_files(len(scenario))

                self.create_script_file(scenario, audio_files, output_dir)
                self.merge_audio_files(audio_files, output_dir)
                
            except OpenAIApiException as e:
                logging.error(e)
                exit(1)

            except Exception as e:
                logging.error(f"An error occurred while generating: {e}, Aborting")
                logging.error(f"Exception type: {type(e).__name__}")
                logging.error(f"Exception message: {e}")
                logging.error(f"Stack trace: {traceback.format_exc()}")
                self.delete_directory(output_dir)
            
            finally:
                self.clean_tmp_dir()
                logging.info("Generation Finished")

    def count_scenarios(self) -> int:
        try:
            directories = [d for d in os.listdir(self.scenarios_dir) if os.path.isdir(os.path.join(self.scenarios_dir, d))]
            return len(directories)
        except Exception as e:
            logging.error(f"Error occurred while counting scenarios: {e}")
            return 0

    def get_increment(self):
        try:
            directories = [d for d in os.listdir(self.scenarios_dir) if os.path.isdir(os.path.join(self.scenarios_dir, d))]
            if not directories:
                return 0
            
            increment = sorted(directories, key=lambda x: int(x))[-1]
            return int(increment) + 1
        except Exception as e:
            logging.error(f"Error occurred while fetching increment: {e}")
            return 1


    def get_next_theme(self) -> str:
        file_path = os.path.join(self.scenarios_dir, "themes.txt")
        themes = []

        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as file:
                pass

        with open(file_path, "r", encoding="utf-8") as file:
            themes = file.read().strip().split('\n')

        if not themes:
            themes = [generate_theme(self.config.dialogue_data) for _ in range(10)]

        theme = themes.pop(0)
        if len(themes) < 10:
            additional_themes_count = 10 - len(themes)
            additional_themes = [generate_theme(self.config.dialogue_data) for _ in range(additional_themes_count)]
            themes.extend(additional_themes)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write('\n'.join(themes))

        logging.info(f"Theme: {theme}")

        return theme
    
    def validate_all_scenario_directories(self):
        for subdirectory in os.listdir(self.scenarios_dir):
            full_subdirectory_path = os.path.join(self.scenarios_dir, subdirectory)
            if os.path.isdir(full_subdirectory_path):
                script_file_path = os.path.join(full_subdirectory_path, "script.txt")
                audio_file_path = os.path.join(full_subdirectory_path, "output.mp3")

                if not (os.path.exists(script_file_path) and os.path.exists(audio_file_path)):
                    logging.warning(f"Missing files in scenario directory {full_subdirectory_path}. Deleting directory.")
                    self.delete_directory(full_subdirectory_path)
                    continue

                if os.path.getsize(script_file_path) == 0 or os.path.getsize(audio_file_path) == 0:
                    logging.warning(f"Empty files detected in scenario directory {full_subdirectory_path}. Deleting directory.")
                    self.delete_directory(full_subdirectory_path)

    def create_script_file(self, dialog, audio_files, output_dir):
        logging.info("Script Creation Started")
        for future in audio_files:
            pos, file_path = future
            if file_path:
                speaker, text = self.parse_line(dialog[pos])
                self.create_script(text, speaker, pos, output_dir)
        logging.info("Script Creation Finished")

    def create_script(self, text, speaker, pos, output_dir):
        try:
            audio_info = mediainfo(os.path.join(self.tmp_dir, f"speech{pos}.mp3"))
            duration = float(audio_info["duration"])
            with open(os.path.join(output_dir, "script.txt"), 'a') as f:
                f.write(f'{speaker}::{text}::{duration}\n')
        except FileNotFoundError:
            logging.error(f"File {self.tmp_dir}/speech{pos}.mp3 not found.")
        except Exception as e:
            logging.error(f"An unexpected error occurred while creating script: {e}")

    def merge_audio_files(self, audio_files, output_dir):
        try:
            logging.info("Audio File Merging Started")
            combined = AudioSegment.empty()
            for pos, file_path in audio_files:
                sound = AudioSegment.from_mp3(file_path)
                combined += sound
            combined.export(os.path.join(output_dir, "output.mp3"), format="mp3")
            logging.info(f"Audio File Merged to {output_dir}/output.mp3")
        except Exception as e:
            logging.error(f"An error occurred while merging audio files: {e}")

    def create_output_directory(self, increment):
        output_dir = f"{self.scenarios_dir}/{increment}"
        os.makedirs(output_dir, exist_ok=True)

        return output_dir

    def generate_scenario(self, theme):
        scenario = self.openai_api.generate_text(self.config.system_prompt, theme)
        if scenario is None or len(scenario) < 1:
            raise ValueError(f"Scenario is empty \"{scenario}\"")
        
        scenario = [s.replace(":", "::", 1) for s in scenario]
        
        return scenario

    def validate_scenario(self, scenario):
        for line in scenario:
            if "::" not in line:
                raise ValueError(f"Invalid scenario format: \"{line}\"")

    def generate_audio_files(self, dialog):
        futures = []
        semaphore = Semaphore(0)
        timeout = 5

        def when_done(future):
            try:
                result = future.result()
                logging.info(f"Process audio thread done: {result}")
                semaphore.release()
            except Exception as e:
                logging.error(f"An error occurred in future: {e}")
                semaphore.release()

        with ThreadPoolExecutor() as executor:
            for pos, line in enumerate(dialog):
                logging.info(f"Process audio for string: {line}")
                speaker, text = self.parse_line(line)
                voice_id = self.get_voice_id(speaker)

                if voice_id:
                    future = executor.submit(self.voice_generator.generate_voice, text, voice_id, pos)
                    future.add_done_callback(when_done)
                    futures.append(future)

        try:
            for _ in range(len(dialog)):
                semaphore.acquire(timeout=timeout)
        except TimeoutError as e:
            logging.error(f"Timed out waiting for futures to complete after {timeout} seconds.")
            raise e

        return [future.result() for future in futures]

    def validate_audio_files(self, expected_count):
        all_files_in_dir = os.listdir(self.tmp_dir)
        actual_count = len(all_files_in_dir)

        logging.info(f"All files in directory '{self.tmp_dir}': {all_files_in_dir}")

        if actual_count != expected_count:
            logging.error(f"Mismatched audio files count. Expected: {expected_count}, Got: {actual_count}")
            raise ValueError("Mismatched audio files count")

    def parse_line(self, line):
        parts = line.split("::")
        return parts[0].strip(), parts[1].strip()

    def get_voice_id(self, speaker):
        return next((char.voice for char in self.config.dialogue_data.characters if char.name == speaker), None)

    def clean_tmp_dir(self):
        try:
            logging.info("Cleanup Started")
            for filename in os.listdir(self.tmp_dir):
                file_path = os.path.join(self.tmp_dir, filename)
                try:
                    os.remove(file_path)
                    logging.debug(f"Deleted file: {file_path}")
                except Exception as e:
                    logging.error(f"Error deleting file {file_path}: {e}")
            logging.info("Cleanup Finished")
        except Exception as e:
            logging.error(f"An unexpected error occurred during cleanup: {e}")

    def delete_directory(self, directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
            except Exception as e:
                logging.error(f"Error deleting file {file_path}: {e}")
        try:
            os.rmdir(directory)
            logging.info(f"Deleted directory: {directory}")
        except Exception as e:
            logging.error(f"Error deleting directory {directory}: {e}")
