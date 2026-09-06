FROM python:3.11-slim

WORKDIR /app

# 1. Устанавливаем системные зависимости для сборки пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 2. Обновляем pip и устанавливаем библиотеки
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]