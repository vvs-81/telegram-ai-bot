import os
import logging
import feedparser

# Импорт из python-telegram-bot 20+
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue,
)
from deep_translator import GoogleTranslator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")               # Ваш токен бота
CHANNEL_ID = os.getenv("CHANNEL_ID", "@my_news") # Ваш канал (например, @my_news)

# RSS-источники (пример)
RSS_FEEDS = [
    "https://hnrss.org/newest",
    "https://www.indiehackers.com/feed.xml",
]

PUBLISHED_FILE = "published_links.txt"

def load_published_links():
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_published_link(link):
    with open(PUBLISHED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def summarize_text(text, max_len=200):
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text

def translate_to_russian(text: str) -> str:
    return GoogleTranslator(source='auto', target='ru').translate(text)

async def fetch_and_post(context: ContextTypes.DEFAULT_TYPE):
    """Функция, которая вызывается JobQueue каждые N минут"""
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)

        for entry in d.entries:
            link = entry.link
            title = entry.title
            summary_text = getattr(entry, 'summary', '')

            if link in published_links:
                continue

            short_summary = summarize_text(summary_text)
            short_summary_ru = translate_to_russian(short_summary)

            msg_text = (
                f"**{title}**\n\n"
                f"{short_summary_ru}\n\n"
                f"Ссылка на оригинал: {link}"
            )

            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg_text,
                    parse_mode="Markdown"
                )
                logging.info(f"Опубликовано: {title}")

                published_links.add(link)
                save_published_link(link)

            except Exception as e:
                logging.error(f"Ошибка при отправке: {e}")

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start (необязательно)"""
    await update.message.reply_text("Бот запущен! Скоро в канале появятся новости.")

def main():
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавляем команду /start
    app.add_handler(CommandHandler("start", start_command))

    # Планировщик (JobQueue)
    job_queue = app.job_queue
    job_queue.run_repeating(fetch_and_post, interval=900, first=10)
    # interval=900 -> каждые 15 минут, first=10 -> через 10 секунд после запуска

    # Запускаем бота (поллинг)
    app.run_polling()

if __name__ == "__main__":
    main()
