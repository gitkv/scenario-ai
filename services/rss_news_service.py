import feedparser
import logging
import time
import re
from models.topic import Topic
from repos.topic_repository import TopicRepository
from models.topic_priority import TopicPriority
from bson import ObjectId
from datetime import datetime
from services.text_filter.text_filter import TextFilter

class RSSNewsService:
    def __init__(self, text_filter: TextFilter, rss_urls: list, topic_repository: TopicRepository, max_rss_topics: int, interval: int = 600):
        self.rss_urls = rss_urls
        self.topic_repository = topic_repository
        self.max_rss_topics = max_rss_topics
        self.text_filter = text_filter
        self.interval = interval

    def remove_html_tags(self, text: str) -> str:
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

    def fetch_news(self):
        news_entries = []
        last_news_date = self.topic_repository.get_latest_rss_topic_date()

        for rss_url in self.rss_urls:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                news_date = datetime(*entry.published_parsed[:6])
                if last_news_date and last_news_date >= news_date:
                    continue
                news_entries.append(entry)

            news_entries = sorted(news_entries, key=lambda x: datetime(*x.published_parsed[:6]))

        for entry in news_entries:
            clean_description = self.remove_html_tags(entry.description)

            topic_text = f"{entry.title}. {clean_description}"

            is_forbidden_text = self.text_filter.is_forbidden(topic_text)
            if(is_forbidden_text):
                logging.warning(f"!!!Text is forbidden: {topic_text}")
                continue

            date = datetime(*entry.published_parsed[:6])
            topic = Topic(
                _id=str(ObjectId()),
                topic_priority=TopicPriority.RSS.value,
                requestor_name="RSS",
                is_allowed=True,
                text=f"Грубо с матом обсуждают новость о том что, {topic_text}",
                created_at=date
            )
            self.topic_repository.create_topic(topic)
            last_news_date = date
            logging.info(f"Added news topic from RSS: {entry.title}")

    def run(self):
        while True:
            try:
                while self.topic_repository.get_rss_topic_count() > self.max_rss_topics:
                    logging.info(f"Reached the maximum rss number of topic ({self.max_rss_topics}). Pausing generation...")
                    time.sleep(self.interval)
                    continue

                self.fetch_news()
                time.sleep(self.interval)
            except Exception as e:
                logging.error(f"Error fetching news from RSS: {e}")
                time.sleep(self.interval)
