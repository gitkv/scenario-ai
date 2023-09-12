import logging
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters, CallbackQueryHandler)

from models.topic import Topic
from models.topic_priority import TopicPriority
from repos.topic_repository import TopicRepository


class TelegramService:
    def __init__(self, token: str, topic_repository: TopicRepository, moderatorId: str):
        self.application = ApplicationBuilder().token(token).build()
        self.topic_repository = topic_repository
        self.first_count = 15
        self.moderatorId = moderatorId
        self.max_topic_lenght = 250
        self.user_messages = {}
        self.help_message = (
            f"/get_topics - Показать очередь тем на обработку (первые {self.first_count} тем).\n"
            "/get_next_topic - Посмотреть какая тема будет обработана следующей.\n"
            "/add_topic текст - Добавить новую тему.\n"
            "/help - Показать эту справку."
        )
        
        start_handler = CommandHandler('start', self.start)
        topics_handler = CommandHandler('get_topics', self.get_topics)
        add_topic_handler = CommandHandler('add_topic', self.add_topic)
        get_next_topic_handler = CommandHandler('get_next_topic', self.get_next_topic)
        help_handler = CommandHandler('help', self.help)
    
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.unknown_command)
        approval_handler = CallbackQueryHandler(self.handle_approval)
        
        self.application.add_handler(start_handler)
        self.application.add_handler(topics_handler)
        self.application.add_handler(add_topic_handler)
        self.application.add_handler(get_next_topic_handler)
        self.application.add_handler(help_handler)
        self.application.add_handler(approval_handler)
        self.application.add_handler(message_handler)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        start_message = (
            "Добро пожаловать в нашего бота! Здесь мы можете управлять нашем эфиром новостей! Вот список доступных команд:\n\n"+self.help_message
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=start_message)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.help_message)

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "Эта команда не поддерживается. Используйте /help чтобы узнать список доступных команд."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        
    async def get_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topics = self.topic_repository.get_n_oldest_topics(self.first_count)

        def truncate_topic_text(text: str) -> str:
            if len(text) > self.max_topic_lenght:
                return text[:self.max_topic_lenght] + "..."
            return text
        
        message = f"Первые {self.first_count} тем в очереди на обработку: \n\n"+'\n'.join([f"🔶 {index + 1}. {truncate_topic_text(topic.text)} \n" for index, topic in enumerate(topics)])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message or "⛔ Очередь тем пуста.")
        
    async def add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        current_timestamp = update.message.date.timestamp()

        # Проверка частоты сообщений
        if user_id in self.user_messages:
            # Удаляем таймстампы, которые старше одной минуты
            self.user_messages[user_id] = [t for t in self.user_messages[user_id] if current_timestamp - t < 60]
            
            # Проверка, отправил ли пользователь более 3 сообщений в последнюю минуту
            if len(self.user_messages[user_id]) >= 3:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Вы отправляете сообщения слишком часто. Пожалуйста, подождите немного.")
                return
        else:
            self.user_messages[user_id] = []

        # Добавляем текущий таймстамп в список
        self.user_messages[user_id].append(current_timestamp)

        topic_text = ' '.join(context.args)
        if not topic_text:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Вы не указали текст темы.")
            return
        
        if len(topic_text) > self.max_topic_lenght:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⛔ Текст темы слишком длинный. Максимальное количество символов: {self.max_topic_lenght}.")
            return

        requestor_name = update.message.from_user.first_name or update.message.from_user.username

        topic = self.topic_repository.create_topic(Topic(
            _id=str(ObjectId()),
            topic_priority=TopicPriority.USER.value,
            requestor_name=requestor_name,
            is_allowed=False,
            text=topic_text
        ))
        await self.send_moderation_request(topic, context)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Ваша тема успешно добавлена в очередь на обработку:\n\n\"{topic_text}\".")
    
    async def get_next_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic = self.topic_repository.get_topic_by_priority()
        if topic:
            message = f"⏩ Следущая тема для обработки:\n\n\"{topic.text}\""
        else:
            message = "⛔ Список тем пуст."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    
    async def send_moderation_request(self, topic: Topic, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить", callback_data=f'approve_{topic.id}'),
            InlineKeyboardButton("❌ Отклонить", callback_data=f'decline_{topic.id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"🆕 Новая тема от {topic.requestor_name}:\n\n{topic.text}"
        await context.bot.send_message(chat_id=self.moderatorId, text=text, reply_markup=reply_markup)

    async def handle_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        verdict_text = ""
        if query.data.startswith('approve_'):
            topic_id = query.data.split('_')[1]
            topic = self.topic_repository.get_topic_by_id(topic_id)
            if topic:
                topic.is_allowed = True
                self.topic_repository.update_topic(topic_id, topic)
                await context.bot.answer_callback_query(callback_query_id=query.id, text="✅ Тема одобрена!")
                verdict_text = "\n\n✅ Тема одобрена!"
            else:
                await context.bot.answer_callback_query(callback_query_id=query.id, text="Ошибка: Тема не найдена!")

        elif query.data.startswith('decline_'):
            await context.bot.answer_callback_query(callback_query_id=query.id, text="❌ Тема отклонена!")
            verdict_text = "\n\n❌ Тема отклонена!"
        
        # Изменяем текст сообщения, добавляя вердикт
        new_text = query.message.text + verdict_text
        await context.bot.edit_message_text(chat_id=query.message.chat_id, 
                                            message_id=query.message.message_id,
                                            text=new_text,
                                            reply_markup=None)

        
    def run(self):
        self.application.run_polling()
