from bson import ObjectId
from pymongo.collection import Collection

from models.story_model import StoryModel
from models.topic_type import TopicType


class StoryRepository:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create_story(self, story: StoryModel):
        self.collection.insert_one(story.dict(by_alias=True))

    def get_story(self, _id: str) -> StoryModel:
        document = self.collection.find_one({"_id": _id})
        if document:
            document['_id'] = str(document['_id'])
            return StoryModel(**document)
        return None

    def update_story(self, _id: str, story: StoryModel):
        self.collection.update_one({"_id": _id}, {"$set": story.dict(by_alias=True)})

    def delete_story(self, id: str):
        id = ObjectId(id)
        self.collection.delete_one({"_id": id})

    def get_total_count(self) -> int:
        return self.collection.count_documents({})

    def get_count_by_topic_type(self, topic_type: TopicType) -> int:
        return self.collection.count_documents({"topic_type": topic_type.value})
