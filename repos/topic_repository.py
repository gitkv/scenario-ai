from typing import List

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.collection import Collection

from models.topic import Topic
from models.topic_type import TopicType


class TopicRepository:
    def __init__(self, collection: Collection):
        self.collection = collection

    def create_topic(self, topic: Topic) -> Topic:
        result = self.collection.insert_one(topic.dict(by_alias=True))
        topic._id = str(result.inserted_id)
        return topic

    def get_topic_by_id(self, id: str) -> Topic:
        document = self.collection.find_one({"_id": id})
        if document:
            return Topic(**document)
        return None
    
    def get_oldest_topic_by_type(self, topic_type: TopicType) -> Topic:
        document = self.collection.find_one({"topic_type": topic_type.value}, sort=[("created_at", ASCENDING)])
        if document:
            document['_id'] = str(document['_id'])
            return Topic(**document)
        return None

    def get_n_oldest_topics(self, n: int) -> List[Topic]:
        documents = self.collection.find().sort("created_at", ASCENDING).limit(n)
        return [Topic(**doc) for doc in documents]

    def get_total_count(self) -> int:
        return self.collection.count_documents({})

    def update_topic(self, id: str, topic: Topic) -> Topic:
        self.collection.update_one({"_id": id}, {"$set": topic.dict(by_alias=True)})
        return self.get_topic_by_id(id)

    def delete_topic(self, id: str):
        id = ObjectId(id)
        self.collection.delete_one({"_id": id})
