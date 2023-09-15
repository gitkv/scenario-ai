import json
import logging

import socketio
from bson import ObjectId

from models.topic import Topic
from models.topic_priority import TopicPriority
from repos.topic_repository import TopicRepository


class DonationAlertsService:
    def __init__(self, da_alert_widget_token, topic_repository: TopicRepository):
        self.da_alert_widget_token = da_alert_widget_token
        self.topic_repository = topic_repository
        self.sio = socketio.Client(reconnection=True, reconnection_delay=5)
        self.setup_events()
        self.threshold_amount_for_super_vip = 200
        
    def setup_events(self):
        @self.sio.on('connect')
        def on_connect():
            self.sio.emit('add-user', {'token': self.da_alert_widget_token, "type": "alert_widget"})
            logging.info('Connected to DonationAlerts socket')

        @self.sio.on('donation')
        def on_message(data):
            event = json.loads(data)
            logging.info(f"Received Donation: {event}")
            self.save_donation_as_topic(event)
        
        @self.sio.on('disconnect')
        def on_disconnect():
            logging.warning('Disconnected from DonationAlerts socket')

        @self.sio.on('connect_error')
        def on_connect_error(error):
            logging.error(f"Connection error: {error}")

        @self.sio.on('reconnect')
        def on_reconnect():
            logging.info('Reconnected to DonationAlerts socket')

        @self.sio.on('reconnect_attempt')
        def on_reconnect_attempt():
            logging.info('Attempting to reconnect to DonationAlerts socket')

        @self.sio.on('reconnect_error')
        def on_reconnect_error(error):
            logging.error(f"Reconnection error: {error}")

        @self.sio.on('reconnect_failed')
        def on_reconnect_failed():
            logging.error('Reconnection to DonationAlerts socket failed')

        @self.sio.on('ping')
        def ping():
            logging.debug('Ping sent to server')

        @self.sio.on('pong')
        def pong(latency):
            logging.debug(f'Pong received from server with latency: {latency}ms')

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
        try:
            self.sio.connect('wss://socket.donationalerts.ru:443', transports='websocket')
            self.sio.wait()
        except Exception as e:
            logging.error(f"Error connecting to DonationAlerts socket: {e}")
