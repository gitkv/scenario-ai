import os
import shutil
from typing import Optional

from pymongo.collection import Collection

from models.story_model import StoryModel
from models.topic_type import TopicType


class StoryRepository:
    def __init__(self, audio_dir: str, collection: Collection):
        self.audio_dir = audio_dir
        self.collection = collection

    def create_story(self, story: StoryModel):
        self.collection.insert_one(story.dict(by_alias=True))

    def get_story(self, id: str) -> StoryModel:
        document = self.collection.find_one({"_id": id})
        if document:
            document['_id'] = str(document['_id'])
            return StoryModel(**document)
        return None

    def update_story(self, id: str, story: StoryModel):
        self.collection.update_one({"_id": id}, {"$set": story.dict(by_alias=True)})

    def delete_story(self, id: str):
        result = self.collection.delete_one({"_id": id})
        
        if result.deleted_count > 0:
            directory_to_delete = os.path.join(self.audio_dir, id)
        
            if os.path.exists(directory_to_delete):
                shutil.rmtree(directory_to_delete)


    def get_total_count(self) -> int:
        return self.collection.count_documents({})

    def get_count_by_topic_type(self, topic_type: TopicType) -> int:
        return self.collection.count_documents({"topic_type": topic_type.value})
    
    def get_story_by_priority(self) -> Optional[StoryModel]:
        document = self.collection.find_one({"topic_type": TopicType.VIP.value})
        
        if document is None:
            document = self.collection.find_one({"topic_type": TopicType.USER.value})

        if document is None:
            document = self.collection.find_one({"topic_type": TopicType.SYSTEM.value})
        
        if document is None:
            return None
        
        document['_id'] = str(document['_id'])
        return StoryModel(**document)