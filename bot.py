import os
import logging
import feedparser
from telegram import Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from googletrans import Translator

# Включаем логи (чтобы было понятно, что происходит)
logging.basicConfig(level=logging.INFO)

# Здесь мы достаём из "переменных окружения" (environment variables) два значения:
# 1) Токен бота
# 2) Название/ID канала
BOT_TOKEN = os.getenv("BOT_TOKEN")         # Туда мы позже подставим свой
CHANNEL_ID = os.getenv("CHANNEL_ID")       # Сюда - например, '@my_ai_rus_news'

# Список RSS-ленточек, откуда тянем новости
RSS_FEEDS = [
    "https://hnrss.org/newest",           # Hacker News (новые)
    "https://www.indiehackers.com/feed.xml",   # Indie Hackers
]

# Файл, чтобы не публиковать одну и ту же ссылку дважды
PUBLISHED_FILE = "published_links.txt"

translator = Translator()

def load_published_links():
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_published_link(link):
    with open(PUBLISHED_FILE, "a") as f:
        f.write(link + "\n")

def summarize_text(text, max_len=200):
    """Обрежем текст до 200 символов, чтобы был короткий анонс"""
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text

def translate_to_russian(text):
    """Переводим на русский googletrans-ом"""
    translated = translator.translate(text, dest='ru')
    return translated.text

def fetch_and_post(context: CallbackContext):
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)

        for entry in d.entries:
            link = entry.link
            title = entry.title
            summary_text = getattr(entry, 'summary', '')

            # Делаем короткое описание
            short_summary = summarize_text(summary_text, 200)
            # Переводим
            short_summary_ru = translate_to_russian(short_summary)

            if link not in published_links:
                # Формируем текст для Телеграма
                msg_text = (
                    f"**{title}**\n\n"
                    f"{short_summary_ru}\n\n"
                    f"Ссылка: {link}"
                )

                try:
                    bot.send_message(chat_id=CHANNEL_ID, text=msg_text, parse_mode='Markdown')
                    save_published_link(link)
                    published_links.add(link)
                except Exception as e:
                    logging.error(f"Ошибка при отправке: {e}")

def start_command(update, context):
    update.message.reply_text("Бот запущен! Скоро появятся первые новости.")

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Команда /start - проверка
    dp.add_handler(CommandHandler("start", start_command))

    # Создаём задачу, которая каждые 15 минут вызывает fetch_and_post
    interval_seconds = 900  # 900 секунд = 15 минут
    job_queue = updater.job_queue
    job_queue.run_repeating(fetch_and_post, interval=interval_seconds, first=10)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
