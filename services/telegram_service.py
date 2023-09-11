import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from models.topic import Topic
from models.topic_priority import TopicPriority
from repos.topic_repository import TopicRepository
from bson import ObjectId

class TelegramService:
    def __init__(self, token: str, topic_repository: TopicRepository):
        self.application = ApplicationBuilder().token(token).build()
        self.topic_repository = topic_repository
        self.first_count = 15
        
        start_handler = CommandHandler('get_topics', self.get_topics)
        add_topic_handler = CommandHandler('add_topic', self.add_topic)
        get_next_topic_handler = CommandHandler('get_next_topic', self.get_next_topic)
        help_handler = CommandHandler('help', self.help)
        message_handler = MessageHandler(filters.TEXT, self.unknown_command)
        
        self.application.add_handler(start_handler)
        self.application.add_handler(add_topic_handler)
        self.application.add_handler(get_next_topic_handler)
        self.application.add_handler(help_handler)
        self.application.add_handler(message_handler)
    

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_message = (
            f"/get_topics - Пказать очередь (первые {self.first_count} тем).\n"
            "/get_next_topic - Посмотреть какая тема будет обработа следующей.\n"
            "/add_topic текст - Добавить новую тему.\n"
            "/help - Показать эту справку."
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=help_message)

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "Эта команда не поддерживается. Используйте /help чтобы узнать список доступных команд."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        
    async def get_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topics = self.topic_repository.get_n_oldest_topics(self.first_count)
        message = f"Первые {self.first_count} тем в очереди: \n\n"+'\n'.join([f"{index + 1}. {topic.requestor_name}: {topic.text} \n" for index, topic in enumerate(topics)])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message or "Очередь тем пуста.")
        
    async def add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic_text = ' '.join(context.args)
        if not topic_text:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Вы не указали текст темы.")
            return
        
        requestor_name = update.message.from_user.first_name or update.message.from_user.username

        self.topic_repository.create_topic(Topic(
            _id=str(ObjectId()),
            topic_priority=TopicPriority.USER.value,
            requestor_name=requestor_name,
            text=topic_text
        ))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Ваша тема успешно добавлена '{topic_text}'.")
    
    async def get_next_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic = self.topic_repository.get_topic_by_priority()
        if topic:
            message = f"Следущая тема для обработки:\n{topic.requestor_name}: {topic.text}"
        else:
            message = "Список тем пуст."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        
    def run(self):
        self.application.run_polling()
