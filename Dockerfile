# Используем официальный образ Python
FROM python:3.10-slim

# Создадим рабочую директорию
WORKDIR /app

# Скопируем файлы requirements.txt и bot.py (Procfile тоже, если нужен)
COPY requirements.txt .
COPY bot.py .
# Если есть Procfile, раскомментируйте строку ниже
# COPY Procfile .

# Установим зависимости
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
CMD ["python", "bot.py"]
