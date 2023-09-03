import logging
import random
import time

from bson import ObjectId
from models.config import DialogueData
from models.topic import Topic
from models.topic_type import TopicType
from repos.topic_repository import TopicRepository


class TopicGenerator:
    def __init__(self, dialogue_data: DialogueData, topic_repository: TopicRepository):
        self.dialogue_data = dialogue_data
        self.topic_repository = topic_repository

    def _generate_topic_text(self) -> str:
        theme_template = random.choice(self.dialogue_data.themes)
        participants = [character.name for character in self.dialogue_data.characters]
        num_participants = random.randint(2, 4)
        chosen_participants = random.sample(participants, num_participants)

        chosen_mood = random.choice(self.dialogue_data.emotions)
        chosen_action = random.choice(self.dialogue_data.actions)
        chosen_topic = random.choice(self.dialogue_data.topics)
        chosen_interaction = random.choice(self.dialogue_data.interactions)

        topic = theme_template.format(
            character1=chosen_participants[0],
            character2=chosen_participants[1] if len(chosen_participants) > 1 else chosen_participants[0],
            character3=chosen_participants[2] if len(chosen_participants) > 2 else chosen_participants[0],
            emotion=chosen_mood,
            action=chosen_action,
            topic=chosen_topic,
            interaction=chosen_interaction
        )

        return topic

    def generate(self):
        while True:
            if self.topic_repository.get_total_count() < 10:
                topic_text = self._generate_topic_text()
                topic = Topic(
                    _id=str(ObjectId()),
                    topic_type=TopicType.SYSTEM.value,
                    requestor_name=TopicType.SYSTEM.value,
                    text=topic_text
                )
                self.topic_repository.create_topic(topic)
                logging.info(f"Generated and saved new theme: {topic_text}")
            else:
                logging.info("Reached the maximum number of topics (10). Pausing generation.")
            
            time.sleep(10)
