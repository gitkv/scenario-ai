from datetime import datetime

from pydantic import BaseModel, Field


class Topic(BaseModel):
    id: str = Field(..., alias='_id')
    topic_type: str
    requestor_name: str
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
