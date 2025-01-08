import os
import logging
import feedparser

from telegram.ext import Updater, CommandHandler, CallbackContext
from deep_translator import GoogleTranslator

# --- ЛОГИ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")             # Токен бота от BotFather
CHANNEL_ID = os.getenv("CHANNEL_ID", "@my_ai_news")  # Ваш канал, например '@my_ai_news'

# --- СПИСОК RSS-ЛЕНТ (пример) ---
RSS_FEEDS = [
    "https://hnrss.org/newest",                # Hacker News (новые)
    "https://www.indiehackers.com/feed.xml",   # Indie Hackers (RSS)
    # Можно добавить свои источники по аналогии
]

# --- ФАЙЛ ДЛЯ ХРАНЕНИЯ "УЖЕ ОПУБЛИКОВАННЫХ" ССЫЛОК ---
PUBLISHED_FILE = "published_links.txt"

# --- ФУНКЦИИ ---

def load_published_links():
    """Считываем уже опубликованные ссылки, чтобы не дублировать."""
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_published_link(link):
    """Сохраняем новую ссылку в файл."""
    with open(PUBLISHED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def summarize_text(text, max_len=200):
    """Обрезаем текст до max_len символов для короткого анонса."""
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text

def translate_to_russian(text):
    """
    Перевод на русский язык при помощи deep-translator.
    По умолчанию source='auto', target='ru' -> Google переведёт автоматически.
    """
    return GoogleTranslator(source='auto', target='ru').translate(text)

def fetch_and_post(context: CallbackContext):
    """Основная функция: парсим ленты, публикуем новые статьи."""
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)

        for entry in d.entries:
            link = entry.link
            title = entry.title
            summary_text = getattr(entry, 'summary', '')

            # Если ссылка уже публиковалась, пропускаем
            if link in published_links:
                continue

            # Делаем короткое резюме
            short_summary = summarize_text(summary_text, 200)
            # Переводим на русский
            short_summary_ru = translate_to_russian(short_summary)

            # Формируем текст для Телеграма (Markdown-разметка)
            msg_text = (
                f"**{title}**\n\n"
                f"{short_summary_ru}\n\n"
                f"Ссылка на оригинал: {link}"
            )

            try:
                bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg_text,
                    parse_mode="Markdown"
                )
                logging.info(f"Опубликовано: {title}")

                # Запоминаем ссылку
                published_links.add(link)
                save_published_link(link)

            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {e}")

def start_command(update, context: CallbackContext):
    """Команда /start в личке бота (необязательная)"""
    update.message.reply_text("Бот запущен! Скоро появятся новые публикации.")

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Регистрируем команду /start
    dp.add_handler(CommandHandler("start", start_command))

    # Планировщик (JobQueue): вызывать fetch_and_post каждые 15 минут
    job_queue = updater.job_queue
    job_queue.run_repeating(fetch_and_post, interval=900, first=10)
    # interval=900 -> 900 секунд = 15 минут
    # first=10 -> первый вызов через 10 секунд после старта бота

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
