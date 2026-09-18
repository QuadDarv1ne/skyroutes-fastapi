"""Gunicorn config для production-запуска SkyRoutes.

Запуск:
    gunicorn app.main:app -c gunicorn_conf.py

Или через переменные окружения:
    BIND=0.0.0.0:8000 WORKERS=4 gunicorn app.main:app -c gunicorn_conf.py
"""
import os
from multiprocessing import cpu_count

# Binding
bind = os.environ.get("BIND", "0.0.0.0:8000")

# Workers — по формуле (2 * CPU) + 1
workers = int(os.environ.get("WORKERS", (cpu_count() * 2) + 1))

# Worker class — uvicorn для поддержки ASGI
worker_class = "uvicorn.workers.UvicornWorker"

# Таймауты
timeout = int(os.environ.get("TIMEOUT", 120))
graceful_timeout = int(os.environ.get("GRACEFUL_TIMEOUT", 30))
keepalive = int(os.environ.get("KEEPALIVE", 5))

# Логирование
accesslog = os.environ.get("ACCESS_LOG", "-")  # "-" = stdout
errorlog = os.environ.get("ERROR_LOG", "-")
loglevel = os.environ.get("LOG_LEVEL", "info")

# Перезагрузка (только для dev)
reload = os.environ.get("RELOAD", "false").lower() == "true"

# Прочее
preload_app = True
max_requests = int(os.environ.get("MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("MAX_REQUESTS_JITTER", 100))
