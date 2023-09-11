import feedparser
import logging
import time
from models.topic import Topic
from repos.topic_repository import TopicRepository
from models.topic_priority import TopicPriority
from bson import ObjectId
from datetime import datetime

class RSSNewsService:
    def __init__(self, rss_url: str, topic_repository: TopicRepository, interval: int = 3600):
        self.rss_url = rss_url
        self.topic_repository = topic_repository
        self.interval = interval
        self.latest_news_date = None

    def fetch_news(self):
        feed = feedparser.parse(self.rss_url)
        
        # Собираем все новости в список
        news_entries = []
        for entry in feed.entries:
            news_date = datetime(*entry.published_parsed[:6])
            if self.latest_news_date and self.latest_news_date >= news_date:
                continue
            news_entries.append(entry)

        # Сортируем новости по дате (сначала самые старые)
        sorted_entries = sorted(news_entries, key=lambda x: datetime(*x.published_parsed[:6]))

        for entry in sorted_entries:
            full_text = entry.get('rbc_news:full-text', '')
            topic_text = f"{entry.title}\n\n{full_text}"

            topic = Topic(
                _id=str(ObjectId()),
                topic_priority=TopicPriority.RSS.value,
                requestor_name="RSS",
                text=topic_text
            )
            self.topic_repository.create_topic(topic)
            logging.info(f"Added news topic from RSS: {entry.title}")
            
            # Обновляем latest_news_date после добавления каждой новости
            self.latest_news_date = datetime(*entry.published_parsed[:6])

    def run(self):
        while True:
            try:
                self.fetch_news()
                time.sleep(self.interval)
            except Exception as e:
                logging.error(f"Error fetching news from RSS: {e}")
                time.sleep(self.interval)
