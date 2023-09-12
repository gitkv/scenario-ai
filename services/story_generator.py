import logging
import os
import re
import shutil
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore
from typing import List

from bson import ObjectId

from models.config import Config
from models.story_model import Scenario, StoryModel
from models.topic import Topic
from models.topic_priority import TopicPriority
from repos import StoryRepository, TopicRepository
from services.openai import OpenAIApi, OpenAIApiException
from services.voice.base_tts import BaseTTS


class StoryGenerator:
    def __init__(self, openai_client: OpenAIApi, config: Config, voice_generator: BaseTTS, audio_dir: str, max_system_stoies: int, topic_repository: TopicRepository, story_repository: StoryRepository):
        self.config = config
        self.audio_dir = audio_dir
        self.openai_api = openai_client
        self.voice_generator = voice_generator
        self.max_system_stoies = max_system_stoies
        self.topic_repository = topic_repository
        self.story_repository = story_repository
        self.delimeter = "::"

        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)

    def generate(self):
        while True:
            
            story_id_str = self._next_story_id()

            try:
                logging.info(f"Generation story started for {story_id_str}")
                self._validate_all_audio_directories()
                topic = self.topic_repository.get_topic_by_priority()

                if not topic:
                    logging.info(f"Not found topics")
                    time.sleep(10)
                    continue

                if topic.topic_priority == TopicPriority.SYSTEM.value and self.story_repository.get_count_by_topic_priority(TopicPriority.SYSTEM) >= self.max_system_stoies:
                    logging.info(f"Reached the maximum system number of story ({self.max_system_stoies}). Pausing generation...")
                    time.sleep(10)
                    continue

                story_text_data = self._generate_story_text(topic.text)
                story_text_data_with_pos = list(enumerate(story_text_data))
                output_dir = self._create_output_directory(story_id_str)

                audio_files = self._generate_audio_files(output_dir, story_text_data)
                audio_files = sorted(audio_files, key=lambda x: x[0])
                time.sleep(1)

                self._validate_audio_files(output_dir, len(story_text_data))

                story_list = []
                for pos, audio_file_path in audio_files:
                    speaker, text = self._parse_line(story_text_data_with_pos[pos][1])
                    story_list.append(Scenario(character=speaker, text=text, sound=audio_file_path))

                logging.debug(story_list)
                    
                story = StoryModel(
                    _id=story_id_str,
                    topic_priority=topic.topic_priority,
                    requestor_name=topic.requestor_name,
                    topic=topic.text,
                    scenario=story_list
                )
                
                logging.debug(story)
                self.story_repository.create_story(story)
                self.topic_repository.delete_topic(topic.id)
                
            except OpenAIApiException as e:
                logging.error(e)
                time.sleep(30)
            
            except ValueError as e:
                logging.error(f"Value error: {e}. Skipping current topic.")
                self.topic_repository.delete_topic(topic.id)

            except Exception as e:
                logging.error(f"An error occurred while generating: {e}, Aborting")
                logging.error(f"Exception type: {type(e).__name__}")
                logging.error(f"Exception message: {e}")
                logging.error(f"Stack trace: {traceback.format_exc()}")
                self.safe_remove_directory(output_dir)
                time.sleep(10)
            
            finally:
                logging.info("Generation finished")

    def _next_story_id(self) -> str:
        return str(ObjectId())
    
    def _validate_all_audio_directories(self):
        for subdirectory in os.listdir(self.audio_dir):
            full_subdirectory_path = os.path.join(self.audio_dir, subdirectory)
            
            if os.path.isdir(full_subdirectory_path):
                if not os.listdir(full_subdirectory_path):
                    logging.warning(f"Empty directory detected: {full_subdirectory_path}. Deleting directory.")
                    self.safe_remove_directory(full_subdirectory_path)


    def _create_output_directory(self, increment):
        output_dir = f"{self.audio_dir}/{increment}"
        os.makedirs(output_dir, exist_ok=True)

        return output_dir

    def _generate_story_text(self, topic_text: str) -> str:
        scenario = self.openai_api.generate_text(self.config.system_prompt, topic_text)
        if scenario is None or len(scenario) < 1:
            raise ValueError(f"story text is empty \"{scenario}\"")
        
        scenario = [s.replace(":", self.delimeter, 1) for s in scenario]
        return self._normalize_scenario(scenario)

    def _normalize_scenario(self, scenario: List[str]) -> List[str]:
        scenario = '\n'.join(scenario)
        scenario = re.sub(r'^assistant::.*$', '', scenario, flags=re.MULTILINE)
        scenario = re.sub(r'^\*\(.*\)\*$', '', scenario, flags=re.MULTILINE)
        scenario = re.sub(r'^\*.*\*$', '', scenario, flags=re.MULTILINE)
        scenario = re.sub(r'^\(.*\)$', '', scenario, flags=re.MULTILINE)
        scenario = re.sub(r'^(?![\w\s]+::).*$', '', scenario, flags=re.MULTILINE)
        scenario = re.sub(r'\n+', '\n', scenario).strip()
        return scenario.split('\n')

    def _validate_story_text(self, scenario):
        for line in scenario:
            if self.delimeter not in line:
                raise ValueError(f"Invalid story text format: \"{line}\"")

    def _generate_audio_files(self, output_dir: str, dialog: str):
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
                speaker, text = self._parse_line(line)
                voice_id = self._get_voice_id(speaker)

                if voice_id:
                    future = executor.submit(self.voice_generator.generate_voice, text, voice_id, output_dir, pos)
                    future.add_done_callback(when_done)
                    futures.append(future)

        try:
            for _ in range(len(dialog)):
                semaphore.acquire(timeout=timeout)
        except TimeoutError as e:
            logging.error(f"Timed out waiting for futures to complete after {timeout} seconds.")
            raise e

        return [future.result() for future in futures]

    def _validate_audio_files(self, output_dir: str, expected_count: int):
        all_files_in_dir = os.listdir(output_dir)
        actual_count = len(all_files_in_dir)

        logging.debug(f"All files in directory '{output_dir}': {all_files_in_dir}")

        if actual_count != expected_count:
            logging.error(f"Mismatched audio files count. Expected: {expected_count}, Got: {actual_count}")
            raise ValueError("Mismatched audio files count")

    def _parse_line(self, line):
        parts = line.split(self.delimeter)
        if len(parts) < 2:
            raise ValueError(f"Invalid line format: {line}")
        return parts[0].strip(), parts[1].strip()

    def _get_voice_id(self, speaker):
        return next((char.voice for char in self.config.dialogue_data.characters if char.name == speaker), None)
    
    def safe_remove_directory(self, path):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
        except Exception as e:
            logging.error(f"Error while removing directory {path}: {e}")

