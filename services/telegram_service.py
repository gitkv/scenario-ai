import logging

from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes, MessageHandler,
                          filters)

from models.topic import Topic
from models.topic_priority import TopicPriority
from repos.topic_repository import TopicRepository
from services.text_filter.text_filter import TextFilter


class TelegramService:
    def __init__(self, token: str, text_filter: TextFilter, topic_repository: TopicRepository, moderatorId: str, donat_url: str):
        self._initialize_handlers(token)
        self.topic_repository = topic_repository
        self.text_filter = text_filter
        self.moderatorId = moderatorId
        self.donat_url = donat_url
        self.first_count = 15
        self.max_topic_lenght = 200
        self.message_count_per_min = 3
        self.user_messages = {}

    def _initialize_handlers(self, token: str):
        self.application = ApplicationBuilder().token(token).build()
        
        handlers = [
            CommandHandler('start', self.start),
            CommandHandler('get_topics', self.get_topics),
            CommandHandler('add_topic', self.add_topic),
            CommandHandler('get_next_topic', self.get_next_topic),
            CommandHandler('rules', self.rules),
            CommandHandler('help', self.help),
            MessageHandler(filters.TEXT & (~filters.COMMAND), self.unknown_command),
            CallbackQueryHandler(self.handle_approval)
        ]
        for handler in handlers:
            self.application.add_handler(handler)

    def _get_help_message(self):
        return (
            "🔹 <b>Список доступных команд:</b>\n\n"
            f"/get_topics - Посмотреть очередь тем на обработку (первые {self.first_count} тем).\n"
            "/get_next_topic - Посмотреть какая тема будет обработана следующей.\n"
            "/add_topic текст - Добавить новую тему. ВАЖНО: Описывайте тему как можно подробно, тогда диалог будет максимально крутым!\n"
            "/rules - Посмотреть правила бота.\n"
            "/help - Посмотреть справку по командам.\n\n"
            f"<a href=\"{self.donat_url}\">Задать свою тему без очереди</a>"
        )

    def _get_rules_message(self):
        return (
            "❗️❗️ <b>Правила использования:</b>\n\n"
            "- Не отправляйте оскорбительные или провокационные сообщения.\n"
            "- Избегайте тем, связанных с политикой, насилием, дискриминацией или экстремизмом.\n"
            "- Будьте уважительны к другим пользователям.\n"
            f"- Ограничение по количеству символов в сообщении темы: {self.max_topic_lenght}.\n"
            "- 👍🏻 Разрешено употребление нецензурных выражений и матерных слов.\nn"
            "Нарушение правил может привести к блокировке вашего доступа к боту.\n\n"
            "💡 <b>О приоритетности тем:</b>\n\n"
            f"- Если вы хотите, чтобы ваша тема была обработана в первую очередь, вы можете поддержать нас <a href=\"{self.donat_url}\">донатом по этой ссылке</a>.\n"
            "- Темы, заданные через этого бота без доната, обрабатываются по мере возможности. При большом количестве желающих время ожидания может возрастать.\n\n"
        )

    def _truncate_topic_text(self, text: str) -> str:
        return text[:self.max_topic_lenght] + "..." if len(text) > self.max_topic_lenght else text

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = (
            "<b>Добро пожаловать в нашего бота!</b>\n\n"
            "🚀 Здесь вы можете предложить свои темы для эфира и посмотреть текущую очередь тем.\n\n"
        )
        start_message = f"{welcome_text}{self._get_rules_message()}{self._get_help_message()}"

        await context.bot.send_message(chat_id=update.effective_chat.id, text=start_message, parse_mode=ParseMode.HTML)


    async def rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self._get_rules_message(), parse_mode=ParseMode.HTML)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self._get_help_message(), parse_mode=ParseMode.HTML)

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "Эта команда не поддерживается.\n\n" + self._get_help_message()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode=ParseMode.HTML)
        
    async def get_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topics = self.topic_repository.get_n_oldest_topics(self.first_count)
        message = (
            f"Первые {self.first_count} тем в очереди на обработку: \n\n" +
            '\n'.join([f"🔶 {index + 1}. {self._truncate_topic_text(topic.text)} \n" for index, topic in enumerate(topics)])
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message or "⛔ Очередь тем пуста.")
        
    async def add_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        current_timestamp = update.message.date.timestamp()

        # Проверка частоты сообщений
        if user_id in self.user_messages:
            # Удаляем таймстампы, которые старше одной минуты
            self.user_messages[user_id] = [t for t in self.user_messages[user_id] if current_timestamp - t < 60]
            
            # Проверка, отправил ли пользователь более n сообщений в последнюю минуту
            if len(self.user_messages[user_id]) >= self.message_count_per_min:
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

        is_forbidden_text = self.text_filter.is_forbidden(topic_text)

        topic = self.topic_repository.create_topic(Topic(
            _id=str(ObjectId()),
            topic_priority=TopicPriority.USER.value,
            requestor_name=requestor_name,
            is_allowed=not is_forbidden_text,
            text=topic_text
        ))
        
        if is_forbidden_text:
            await self.send_moderation_request(topic, context)
            added_text=f"✅ Ваша тема добавлена, но требует модерации из-за возможного нарушения правил:\n\n\"{topic_text}\"."
        else:
            added_text=f"✅ Ваша тема успешно добавлена в очередь на обработку:\n\n\"{topic_text}\"."

        await context.bot.send_message(chat_id=update.effective_chat.id, text=added_text)
    
    async def get_next_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic = self.topic_repository.get_topic_by_priority()
        if topic:
            message = f"⏩ Следущая тема для обработки:\n\n\"{topic.text}\""
        else:
            message = "⛔ Список тем пуст."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    
    async def send_moderation_request(self, topic: Topic, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[
            InlineKeyboardButton("✅ Одобрить", callback_data=f'approve_{topic.id}'),
            InlineKeyboardButton("❌ Отклонить", callback_data=f'decline_{topic.id}')
        ]]
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
        await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text=new_text, reply_markup=None)
        
    def run(self):
        self.application.run_polling()
