from dataclasses import dataclass
from typing import List

@dataclass
class Character:
    name: str
    voice: str

@dataclass
class DialogueData:
    characters: List[Character]
    emotions: List[str]
    interactions: List[str]
    actions: List[str]
    topics: List[str]
    themes: List[str]

@dataclass
class Config:
    system_prompt: str
    telegram_token: str
    da_alert_widget_token: str
    rss_urls: List[str]
    voice_generator: str
    dialogue_data: DialogueData
