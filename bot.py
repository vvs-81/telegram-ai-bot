import os
import logging
import feedparser

# Импорт из python-telegram-bot 20+
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue
)
from deep_translator import GoogleTranslator

# Логи
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")               # Токен бота (от BotFather)
CHANNEL_ID = os.getenv("CHANNEL_ID", "@my_news") # Ваш канал, например '@my_news'

# RSS-ленты
RSS_FEEDS = [
    "https://hnrss.org/newest",                
    "https://www.indiehackers.com/feed.xml",   
]

# Файл для хранения «уже опубликованных» ссылок
PUBLISHED_FILE = "published_links.txt"


# --- Вспомогательные функции ---

def load_published_links():
    """Считываем уже опубликованные ссылки."""
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_published_link(link):
    """Сохраняем ссылку в файл."""
    with open(PUBLISHED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def summarize_text(text, max_len=200):
    """Обрезаем текст до max_len символов."""
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text

def translate_to_russian(text: str) -> str:
    """Перевод на русский язык с помощью deep-translator (GoogleTranslator)."""
    return GoogleTranslator(source='auto', target='ru').translate(text)


# --- Функция, которую будем запускать каждые N минут (через JobQueue) ---

async def fetch_and_post(context: ContextTypes.DEFAULT_TYPE):
    """Основная логика парсинга RSS и отправки в канал."""
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)

        for entry in d.entries:
            link = entry.link
            title = entry.title
            summary_text = getattr(entry, 'summary', '')

            # Проверяем, публиковали ли мы уже это
            if link in published_links:
                continue

            # Делаем короткий анонс + переводим
            short_summary = summarize_text(summary_text, 200)
            short_summary_ru = translate_to_russian(short_summary)

            # Формируем текст для Telegram (Markdown)
            msg_text = (
                f"**{title}**\n\n"
                f"{short_summary_ru}\n\n"
                f"Ссылка на оригинал: {link}"
            )

            # Публикуем
            try:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=msg_text,
                    parse_mode="Markdown"
                )
                logging.info(f"Опубликовано: {title}")

                # Сохраняем ссылку
                published_links.add(link)
                save_published_link(link)

            except Exception as e:
                logging.error(f"Ошибка при отправке: {e}")


# --- Команда /start (необязательно) ---

async def start_command(update, context):
    """Обработчик команды /start в личке бота."""
    await update.message.reply_text("Бот запущен! Скоро появятся новые статьи в канале.")


# --- Основная точка входа ---

def main():
    # Создаём приложение (Application) c помощью билдера
    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчик команды /start
    app.add_handler(CommandHandler("start", start_command))

    # Планировщик задач (JobQueue)
    job_queue = app.job_queue
    # Запускать fetch_and_post каждые 900 секунд (15 мин), первый раз через 10 сек
    job_queue.run_repeating(fetch_and_post, interval=30, first=10)

    # Запускаем "бесконечный" цикл бота (поллинг)
    app.run_polling()

# Точка входа
if __name__ == "__main__":
    main()
