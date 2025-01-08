import os
import logging
import feedparser
from telegram import Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO)

# Забираем из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")        # Ваш токен от BotFather
CHANNEL_ID = os.getenv("CHANNEL_ID")      # Название канала, например "@my_ai_rus_news"

# RSS-ленты, которые будем проверять
RSS_FEEDS = [
    "https://hnrss.org/newest",
    "https://www.indiehackers.com/feed.xml",
    # Добавляйте другие ленты по желанию
]

# Файл, чтобы не дублировать одну и ту же ссылку повторно
PUBLISHED_FILE = "published_links.txt"

# --- Ключевые слова для фильтрации ---
AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "искусственный интеллект",
    "чатgpt"  
}

MONEY_KEYWORDS = {
    "profit",
    "money",
    "revenue",
    "earn",
    "earning",
    "monetize",
    "monetization",
    "заработок",
    "доход",
    "прибыль",
    "деньги"
}

SOLO_KEY
