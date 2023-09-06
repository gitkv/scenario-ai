from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    character: str
    text: str
    sound: str

class StoryModel(BaseModel):
    id: str = Field(..., alias='_id')
    topic_type: str
    requestor_name: str
    topic: str
    scenario: List[Scenario]
    created_at: datetime = Field(default_factory=datetime.utcnow)
