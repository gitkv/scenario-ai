from datetime import datetime

from pydantic import BaseModel, Field


class Topic(BaseModel):
    id: str = Field(..., alias='_id')
    topic_priority: int
    requestor_name: str
    is_allowed: bool
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
