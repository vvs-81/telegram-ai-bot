import os
import logging
import feedparser

from deep_translator import GoogleTranslator
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@my_ai_channel")  # Замените на своё

# === СПИСОК RSS-ЛЕНТ, ГДЕ ЧАСТО ПОЯВЛЯЮТСЯ ИНДИ-ПРЕДПРИНИМАТЕЛИ ИЛИ AI-ПРОЕКТЫ ===
RSS_FEEDS = [
    "https://hnrss.org/newest",
    "https://www.indiehackers.com/feed.xml",
    "https://bootstrappers.io/feed",
    "https://bensbites.substack.com/feed",
    "https://dev.to/feed/t/bootstrapping",
    "https://thebootstrappedfounder.com/blog/feed/",
]

# === КЛЮЧЕВЫЕ СЛОВА ===

AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "искусственный интеллект",
    "chatgpt",
    "gpt"
}

MONEY_KEYWORDS = {
    "money",
    "profit",
    "revenue",
    "earn",
    "earning",
    "monetize",
    "monetization",
    "заработок",
    "прибыль",
    "доход"
}

SOLO_KEYWORDS = {
    "solo founder",
    "one founder",
    "single founder",
    "solopreneur",
    "один основатель",
    "соло основатель",
    "indiehacker",  # иногда встречается слитно
    "indie hacker", 
    "no employees"
}

NO_INVESTOR_KEYWORDS = {
    "bootstrapped",
    "bootstrapping",
    "no investor",
    "no investors",
    "без инвестиций",
    "self-funded",
    "no vc",
    "no external funding",
    "no outside funding"
}

PUBLISHED_FILE = "published_links.txt"

# === ФУНКЦИИ ===

def load_published_links():
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_published_link(link):
    with open(PUBLISHED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def translate_to_russian(text: str) -> str:
    """Переводим заголовок на русский язык через Google (deep_translator)."""
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        logging.error(f"Ошибка при переводе: {e}")
        return text

def is_ai_article(title: str) -> bool:
    """Проверяем, относится ли заголовок к AI."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in AI_KEYWORDS)

def is_solo_earning_article(title: str) -> bool:
    """
    Проверяем, есть ли в заголовке упоминания о заработке + соло-основателе + отсутствии инвестиций.
    Нужно, чтобы совпали три группы:
    1) MONEY_KEYWORDS
    2) SOLO_KEYWORDS
    3) NO_INVESTOR_KEYWORDS
    """
    text_lower = title.lower()
    has_money = any(m in text_lower for m in MONEY_KEYWORDS)
    has_solo = any(s in text_lower for s in SOLO_KEYWORDS)
    has_no_investor = any(i in text_lower for i in NO_INVESTOR_KEYWORDS)

    return (has_money and has_solo and has_no_investor)

def is_relevant_article(title: str) -> bool:
    """
    Статья релевантна, если:
    - ЛИБО заголовок относится к AI
    - ЛИБО заголовок про заработок (MONEY) + соло-основателя (SOLO) + без инвесторов (NO_INVESTOR)
    """
    return is_ai_article(title) or is_solo_earning_article(title)


# === ОСНОВНАЯ ФУНКЦИЯ ДЛЯ ПУБЛИКАЦИЙ ===
async def fetch_and_post(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    published_links = load_published_links()

    for feed_url in RSS_FEEDS:
        d = feedparser.parse(feed_url)

        for entry in d.entries:
            link = entry.link
            title_en = entry.title  # оригинальный заголовок (англ. чаще всего)

            if link in published_links:
                continue

            # Проверяем, релевантна ли статья
            if not is_relevant_article(title_en):
                continue

            # Переводим заголовок на русский
            title_ru = translate_to_russian(title_en)

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

                published_links.add(link)
                save_published_link(link)
            except Exception as e:
                logging.error(f"Ошибка при отправке: {e}")


# === /start — ДЛЯ ТЕСТА (НЕОБЯЗАТЕЛЬНО) ===
async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот запущен! Ищу статьи по AI ИЛИ про заработок с соло-основателем без инвестиций."
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))

    # Каждые 15 минут бот парсит RSS
    job_queue = app.job_queue
    job_queue.run_repeating(fetch_and_post, interval=900, first=10)

    app.run_polling()


if __name__ == "__main__":
    import sys
    if not BOT_TOKEN:
        logging.error("Не установлен BOT_TOKEN в переменных окружения!")
        sys.exit(1)

    main()
