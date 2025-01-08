import os
import logging
import feedparser

# Библиотека для перевода (Google Translator):
from deep_translator import GoogleTranslator

# Импорты из новой версии python-telegram-bot (v20+):
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# Включаем логи
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "")                 # Токен бота (BotFather)
CHANNEL_ID = os.getenv("CHANNEL_ID", "@my_ai_channel") # Ваш канал, например @my_ai_channel

# === RSS-ЛЕНТЫ, КОТОРЫЕ МЫ ОБСУЖДАЛИ В НАЧАЛЕ ===
# (Выбираем те, у которых точно есть RSS)
RSS_FEEDS = [
    "https://hnrss.org/newest",                 # Hacker News (новые)
    "https://www.indiehackers.com/feed.xml",    # Indie Hackers
    "https://bootstrappers.io/feed",            # Bootstrappers.io
    # Substack Ben's Bites (пример):
    "https://bensbites.substack.com/feed"
    # Product Hunt — официального RSS нет, поэтому пропустим
]

# === КЛЮЧЕВЫЕ СЛОВА ДЛЯ AI (Простая фильтрация) ===
AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "искусственный интеллект",
    "chatgpt",
    "gpt"
}

# === ФАЙЛ ДЛЯ ХРАНЕНИЯ УЖЕ ОПУБЛИКОВАННЫХ ССЫЛОК ===
PUBLISHED_FILE = "published_links.txt"


def load_published_links():
    """Считываем уже опубликованные ссылки, чтобы не дублировать."""
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)


def save_published_link(link):
    """Сохраняем ссылку, которую уже опубликовали."""
    with open(PUBLISHED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def is_ai_related(title: str) -> bool:
    """
    Простая проверка, упоминается ли ИИ (AI) в заголовке,
    чтобы не брать всё подряд.
    """
    title_lower = title.lower()
    return any(kw in title_lower for kw in AI_KEYWORDS)


def translate_to_russian(text: str) -> str:
    """
    Переводим заголовок на русский язык (через deep-translator → Google).
    """
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        logging.error(f"Ошибка перевода: {e}")
        return text  # Если сбой, вернём оригинал


async def fetch_and_post(context: ContextTypes.DEFAULT_TYPE):
    """
    Функция, которую периодически вызывает JobQueue: 
    парсим RSS-ленты, фильтруем статьи по AI, переводим заголовок, публикуем.
    """
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)

        for entry in d.entries:
            link = entry.link
            title_en = entry.title

            # Проверяем, не публиковали ли уже
            if link in published_links:
                continue

            # Фильтруем: ищем упоминание AI-слов в заголовке
            if not is_ai_related(title_en):
                continue

            # Переводим заголовок на русский
            title_ru = translate_to_russian(title_en)

            # Формируем текст для Telegram
            msg_text = (
                f"**{title_ru}**\n\n"
                f"Ссылка на оригинал: {link}"
            )

            # Публикуем в канал
            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg_text,
                    parse_mode="Markdown"
                )
                logging.info(f"Опубликовано: {title_en}")

                # Запоминаем ссылку
                published_links.add(link)
                save_published_link(link)

            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {e}")


async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start в личке бота (необязательно)"""
    await update.message.reply_text("Бот запущен! Статьи по AI будут публиковаться в канале.")


def main():
    # Создаём объект приложения
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Добавляем команду /start
    app.add_handler(CommandHandler("start", start_command))

    # Подключаем JobQueue (каждые 15 минут проверяем ленты)
    job_queue = app.job_queue
    job_queue.run_repeating(fetch_and_post, interval=900, first=10)
    # interval=900 секунд (15 минут), first=10 секунд.

    # Запускаем "бесконечный" цикл обработки
    app.run_polling()


# Запуск
if __name__ == "__main__":
    import sys
    if not BOT_TOKEN:
        logging.error("Не задан BOT_TOKEN! Укажите его в переменных окружения.")
        sys.exit(1)

    main()
