import json
import logging
import time

import requests
from bs4 import BeautifulSoup
from bson import ObjectId

from models.topic import Topic
from models.topic_priority import TopicPriority
from repos.topic_repository import TopicRepository


class DonationAlertsParserService:

    def __init__(self, token, topic_repository: TopicRepository):
        self.url = f"https://www.donationalerts.com/widget/lastdonations?alert_type=1&limit=100&token={token}"
        self.topic_repository = topic_repository
        self.processed_donation_ids = set()
        self.threshold_amount_for_super_vip = 200
        self.seconds_for_wait = 30

    def fetch_and_save_donations(self):
        donations = self.get_donations_from_page()

        for donation in donations:
            donation_id = donation["id"]
            if donation_id not in self.processed_donation_ids:
                self.save_donation_as_topic(donation)
                self.processed_donation_ids.add(donation_id)

    def get_donations_from_page(self):
        response = requests.get(self.url)
        if response.status_code != 200:
            logging.error(f"Failed to fetch the page. Status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        event_container = soup.find('div', class_='event-container b-last-events-widget__list s-last-events-container')
        script_tag = event_container.find('script')

        if not script_tag or not script_tag.string:
            logging.error("Script tag not found or it's empty")
            return []

        donation_data = []
        for line in script_tag.string.splitlines():
            if "addEvent(" in line:
                original_json_str = line.strip().replace("addEvent(", "").replace(");", "")
                try:
                    decoded_json_str = original_json_str.encode().decode('unicode_escape')
                    decoded_json_str = decoded_json_str.strip()
                    decoded_json_str = decoded_json_str[1:-1]
                    
                    donation = json.loads(decoded_json_str)
                    
                    if 'additional_data' in donation and isinstance(donation['additional_data'], str):
                        try:
                            donation['additional_data'] = json.loads(donation['additional_data'])
                        except json.JSONDecodeError:
                            pass

                    donation_data.append(donation)
                except json.JSONDecodeError as jde:
                    logging.error(f"Error parsing JSON: {decoded_json_str}. Reason: {jde}. Original: {original_json_str[:100]}")

        return donation_data

    def save_donation_as_topic(self, event):
        logging.info(f"!!!Новый донат от {event['username']} на сумму {event['amount']} {event['currency']}. Сообщение: {event['message']}")

        if float(event['amount']) >= self.threshold_amount_for_super_vip:
            priority = TopicPriority.SUPER_VIP
        else:
            priority = TopicPriority.VIP

        topic = Topic(
            _id=str(ObjectId()),
            topic_priority=priority.value,
            requestor_name=event['username'],
            is_allowed=True,
            text=event['message']
        )
        self.topic_repository.create_topic(topic)

    def start(self):
        while True:
            try:
                self.fetch_and_save_donations()
                time.sleep(self.seconds_for_wait)
            except Exception as e:
                logging.error(f"Error while fetching and saving donations: {e}")
