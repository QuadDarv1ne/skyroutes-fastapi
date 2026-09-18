# === Сборочный образ ===
FROM python:3.12-slim AS builder

WORKDIR /app

# Системные зависимости для сборки bcrypt и asyncpg/psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# === Runtime-образ ===
FROM python:3.12-slim

WORKDIR /app

# Только runtime-зависимости (без build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты
COPY --from=builder /install /usr/local

# Копируем код приложения
COPY app/ ./app/
COPY run.py ./
COPY gunicorn_conf.py ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY README.md ./
COPY .env.example ./

# Создаём непривилегированного пользователя
RUN useradd -m -u 1000 skyroutes && chown -R skyroutes:skyroutes /app
USER skyroutes

EXPOSE 8000

# По умолчанию запускаем через gunicorn (production)
# Для dev-режима используйте: docker run skyroutes uvicorn app.main:app --reload
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py", "--bind", "0.0.0.0:8000"]
