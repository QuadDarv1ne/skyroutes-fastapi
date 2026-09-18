# === SkyRoutes Makefile ===
# Удобные команды для разработки.

PYTHON ?= python
VENV   ?= .venv
PIP    := $(VENV)/bin/pip
PY     := $(VENV)/bin/python
PORT   ?= 8000

.PHONY: help venv install seed run dev test test-api clean docker-up docker-down

help:  ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "} {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv:  ## Создать виртуальное окружение
	$(PYTHON) -m venv $(VENV)

install:  ## Установить зависимости
	$(PIP) install -r requirements.txt

seed:  ## Заполнить БД тестовыми данными
	$(PY) -m app.seed

run:  ## Запустить production-сервер (uvicorn без reload)
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

dev:  ## Запустить dev-сервер (uvicorn с reload)
	$(VENV)/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

test:  ## Запустить pytest-тесты
	$(PY) -m pytest tests/ -v

test-api:  ## Запустить интеграционный smoke-тест API
	$(PY) scripts/test_api.py

clean:  ## Удалить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache *.db *.log

docker-up:  ## Запустить через docker compose
	docker compose up --build

docker-down:  ## Остановить docker compose
	docker compose down
