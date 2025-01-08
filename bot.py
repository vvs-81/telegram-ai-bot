import os
import logging
import feedparser
from telegram import Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from googletrans import Translator

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")         # Токен бота
CHANNEL_ID = os.getenv("CHANNEL_ID")       # Ваш канал, например @my_ai_startup_news

RSS_FEEDS = [
    "https://hnrss.org/newest",            
    "https://www.indiehackers.com/feed.xml",
    # Можно добавить ещё источники
]

PUBLISHED_FILE = "published_links.txt"
translator = Translator()

# --- КЛЮЧЕВЫЕ СЛОВА ---

AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "чатgpt",         # Добавим и кириллические варианты, если нужно
    "искусственный интеллект"
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

SOLO_KEYWORDS = {
    "solo founder",
    "single founder",
    "indie",
    "bootstrapped",
    "no employees",
    "one-man",
    "solopreneur",
    "no investment",
    "без инвестиций",
    "один основатель",
    "индие",
    "бутстрап",
}

def load_published_links():
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_published_link(link):
    with open(PUBLISHED_FILE, "a") as f:
        f.write(link + "\n")

def summarize_text(text, max_len=200):
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text

def translate_to_russian(text):
    translated = translator.translate(text, dest='ru')
    return translated.text

def is_relevant_article(title, summary):
    """
    Проверяем, упоминается ли ИИ, заработок и факт "соло-предпринимательства".
    """
    # Приведём к нижнему регистру, чтобы искать ключевые слова
    text_lower = (title + " " + summary).lower()

    # Нужно, чтобы статья содержала хотя бы одно слово из AI_KEYWORDS,
    # одно из MONEY_KEYWORDS и одно из SOLO_KEYWORDS
    has_ai = any(kw in text_lower for kw in AI_KEYWORDS)
    has_money = any(kw in text_lower for kw in MONEY_KEYWORDS)
    has_solo = any(kw in text_lower for kw in SOLO_KEYWORDS)

    return has_ai and has_money and has_solo

def fetch_and_post(context: CallbackContext):
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)
        for entry in d.entries:
            link = entry.link
            title = entry.title
            summary_text = getattr(entry, 'summary', '')

            if link in published_links:
                # Уже публиковали — пропускаем
                continue

            # Смотрим, подходит ли статья под наши критерии
            if not is_relevant_article(title, summary_text):
                continue

            # Делать саммари и перевод (если нужно)
            short_summary = summarize_text(summary_text, 200)
            short_summary_ru = translate_to_russian(short_summary)

            # Формируем сообщение
            msg_text = (
                f"**{title}**\n\n"
                f"{short_summary_ru}\n\n"
                f"Ссылка на оригинал: {link}"
            )

            # Публикуем в канал
            try:
                bot.send_message(chat_id=CHANNEL_ID, text=msg_text, parse_mode="Markdown")
                save_published_link(link)
                logging.info(f"Опубликовано: {title}")
            except Exception as e:
                logging.error(f"Ошибка отправки: {e}")

def start_command(update, context):
    update.message.reply_text("Бот запущен! Ждите свежие статьи по AI, заработку и соло-стартапам.")

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_command))

    # Каждые 15 минут проверяем ленты
    interval_seconds = 900
    job_queue = updater.job_queue
    job_queue.run_repeating(fetch_and_post, interval=interval_seconds, first=10)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
