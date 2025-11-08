# New Car Sell Notify API

FastAPI-сервис для приема уведомлений о новых объявлениях по продаже автомобилей и выдачи накопленных уведомлений потребителю (например, Telegram-боту). Хранилище — Redis (асинхронный клиент), операции добавления/чтения выполняются атомарно с использованием распределенных блокировок.

- Язык/Runtime: Python 3.12+
- Веб-фреймворк: FastAPI + Starlette
- Валидация: Pydantic v2 (+ pydantic-extra-types для телефонов)
- Хранилище: Redis (через redis.asyncio)
- Конфигурация: pydantic-settings (переменные окружения, .env)
- Запуск: Docker Compose (Redis + API под Gunicorn), локально через Uvicorn (опционально)


## Кратко о проекте

Сервис предоставляет два основных сценария:

1) Прием уведомления: POST /v1/notify/ — принимает данные объявления (URL, аналитика, телефон продавца) и сохраняет в Redis-список под блокировкой.
2) Выдача и очистка: GET /v1/notify/ — отдаёт список накопленных уведомлений и сразу очищает их в Redis под блокировкой. По умолчанию возвращает до 100 последних записей.

Здоровье сервиса проверяется эндпоинтом GET /v1/lifecheck/.


## Структура репозитория (основное)

- `main.py` — инициализация приложения FastAPI, регистрация роутеров, lifespan. В проде отключаются Swagger/Redoc/OpenAPI через конфиг.
- `docker-compose.yml` — поднимает Redis и API. Порты берутся из `.env`, доступ только с `127.0.0.1`.
- `Dockerfile.api` — сборка образа API (Gunicorn + 4 воркера + uvicorn worker).
- `.dockerignore` — оптимизация сборки образа.
- `requirements.txt` — зафиксированные зависимости (включая `pydantic-settings`).
- `pyproject.toml` — метаданные проекта.
- `REDIS_STREAMS_GUIDE.md` — заметки по альтернативе на Redis Streams.
- `тз.md` — краткое ТЗ.

Код приложения:

- `app/api/v1/routes/lifecheck.py` — healthcheck эндпоинт.
- `app/api/v1/routes/notify.py` — приём уведомления (POST) и получение списка (GET).
- `app/api/v1/schemas/notify.py` — Pydantic-схемы запросов/ответов.
- `app/api/dependencies/redis.py` — зависимости FastAPI для DI (Redis-клиент, менеджер уведомлений).
- `app/api/service/redis/redis_client.py` — инициализация асинхронного клиента Redis из настроек.
- `app/api/service/redis/new_notifications.py` — менеджер уведомлений: добавление, атомарное чтение+очистка с блокировкой.
- `app/config/config_reader.py` — pydantic-settings: чтение `.env`/окружения (UTF-8). Поддерживает флаги окружения.


## Архитектура и поток данных

- Клиент отправляет уведомление в API: POST /v1/notify/.
- `NewNotificationsManager.add_notification` сериализует данные в JSON и добавляет в Redis-список (`LPUSH`) под распределенной блокировкой.
- Потребитель (бот/сервис) запрашивает GET /v1/notify/.
- `NewNotificationsManager.get_notifications` под блокировкой читает до 100 элементов (`LRANGE`), десериализует и удаляет ключ со списком — тем самым атомарно «забирает и очищает» пул уведомлений.

В `REDIS_STREAMS_GUIDE.md` описана альтернативная реализация на Redis Streams (подойдет, если понадобится история, consumer groups и т.п.). Текущая реализация использует списки для простоты и минимальной задержки.


## API

Базовый префикс версионирования: `/v1`.

Документация Swagger/OpenAPI (если не отключена окружением):
- Swagger UI: http://127.0.0.1:${FASTAPI_PORT}/docs (по умолчанию порт 8000)
- ReDoc: http://127.0.0.1:${FASTAPI_PORT}/redoc

Важно: при `ENV=production` документация и схема OpenAPI отключены (см. ниже «Окружения»).

### Healthcheck

- GET `/v1/lifecheck/`
- Пример ответа: `{ "lifecheck": true }`

### Уведомления

1) POST `/v1/notify/`

	Тело запроса (JSON):

	```json
	{
	  "advert_url": "https://example.com/car/123",
	  "analytics": "Популярная модель, хорошая цена",
	  "seller_phone": "+7 999 123-45-67"
	}
	```

	Успешный ответ:

	```json
	{
	  "success": true,
	  "message": "Уведомление успешно добавлено"
	}
	```

2) GET `/v1/notify/`

	Успешный ответ:

	```json
	{
	  "data": [
	    {
	      "advert_url": "https://example.com/car/123",
	      "analytics": "Популярная модель, хорошая цена",
	      "seller_phone": "+7 999 123-45-67"
	    }
	  ]
	}
	```

	Примечания:
	- Возвращает до 100 уведомлений за раз (настройка по умолчанию в менеджере).
	- После успешной выдачи список в Redis очищается (атомарно, под блокировкой).


## Модели данных (Pydantic)

- `NewCarNotify`:
	- `advert_url: HttpUrl`
	- `analytics: str`
	- `seller_phone: PhoneNumber`

- `NewCarNotifyResponse`:
	- `success: bool`
	- `message: str = "Уведомление успешно добавлено"`

- `NewCarNotifyListResponse`:
	- `data: list[NewCarNotify]`


## Конфигурация и окружения

Читается из окружения и `.env` (UTF-8), см. `app/config/config_reader.py`.

Поддерживаемые переменные окружения:

- `FASTAPI_HOST` (str, по умолчанию `localhost`) — используется для локальных запусков.
- `FASTAPI_PORT` (int, по умолчанию `8000`) — публикуемый порт API (также используется в `docker-compose.yml`).
- `REDIS_HOST` (str, по умолчанию `localhost`) — снаружи контейнеров. В Docker-сети API использует имя сервиса Redis.
- `REDIS_PORT` (int, по умолчанию `6379`)
- `REDIS_DB` (int, по умолчанию `0`)
- `REDIS_PASSWORD` (str | null, по умолчанию `None`)
- `ENV` (str, `development` | `production`, по умолчанию `development`)

Пример `.env` (см. `.env.template`):

```env
# FastAPI
FASTAPI_HOST=localhost
FASTAPI_PORT=8000

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_password

# Окружение
ENV=development  # или production
```

Особенности прод-режима:

- При `ENV=production` внутри приложения отключаются Swagger `/docs`, ReDoc `/redoc` и OpenAPI `/openapi.json`.
- В `docker-compose.yml` для сервиса API явно задано `ENV=production`. Для включения документации в контейнере — измените на `ENV=development` или удалите эту строку (тогда значение возьмётся из `.env`).


## Запуск в Docker (рекомендуется)

1) Подготовить `.env` (при необходимости скопировать из шаблона):

```bash
cp .env.template .env
```

2) Запустить сервисы (Redis + API):

```bash
docker compose up -d --build
```

3) Проверка:

- Healthcheck: http://127.0.0.1:${FASTAPI_PORT}/v1/lifecheck/
- Документация (только если `ENV=development` для API): http://127.0.0.1:${FASTAPI_PORT}/docs

Остановка и очистка данных Redis volume:

```bash
docker compose down --volumes
```

Что поднимает Compose:

- Redis: образ `redis:7-alpine`, порт `127.0.0.1:${REDIS_PORT}->6379`, volume для данных.
- API: сборка из `Dockerfile.api`, Gunicorn (4 воркера, `uvicorn.workers.UvicornWorker`), порт `127.0.0.1:${FASTAPI_PORT}->8000`.
- В контейнере API переменная `REDIS_HOST` переопределяется на `new_car_sell_notify_service_redis` (имя сервиса) для работы по Docker-сети.


## Локальный запуск без Docker (опционально)

Требования: Python 3.12+ и локальный Redis (либо через Docker из предыдущего раздела).

1) Установить зависимости:

```bash
python -m pip install -r requirements.txt
```

2) Запустить приложение разработчика (горячая перезагрузка):

```bash
uvicorn main:app --reload
```

Проверка:

- http://127.0.0.1:${FASTAPI_PORT}/v1/lifecheck/
- http://127.0.0.1:${FASTAPI_PORT}/docs (если `ENV=development`)


## Примеры запросов (curl)

Добавить уведомление:

```bash
curl -X POST http://127.0.0.1:${FASTAPI_PORT}/v1/notify/ \
  -H "Content-Type: application/json" \
  -d '{
    "advert_url": "https://example.com/car/123",
    "analytics": "Популярная модель, хорошая цена",
    "seller_phone": "+7 999 123-45-67"
  }'
```

Получить и очистить уведомления:

```bash
curl http://127.0.0.1:${FASTAPI_PORT}/v1/notify/
```


## Технические детали

- Менеджер уведомлений: `app/api/service/redis/new_notifications.py`
  - `add_notification(notification: dict)` — `LPUSH` JSON-строки под блокировкой.
  - `get_notifications(count: int = 100)` — `LRANGE` + атомарная очистка ключа под блокировкой.
- Клиент Redis: `app/api/service/redis/redis_client.py` — создается из `env_config`.
- DI-зависимости: `app/api/dependencies/redis.py` — предоставляет клиент и менеджер в роуты.
- Роуты: `app/api/v1/routes/notify.py`, `app/api/v1/routes/lifecheck.py`.
- Создание FastAPI-приложения завернуто в приватный метод `FastAPIapp._create_app()`, который учитывает `ENV` для отключения документации в проде.


## Дорожная карта / улучшения

- Опционально перейти на Redis Streams (см. `REDIS_STREAMS_GUIDE.md`) для поддержки consumer groups и истории.
- Добавить пагинацию/лимиты в GET `/v1/notify/` (параметры запроса).
- Добавить аутентификацию/авторизацию для эндпоинтов, если сервис выходит наружу.
- Добавить тесты (юнит и интеграционные) и CI.


## Лицензия

Не указана. При необходимости добавьте файл `LICENSE` и раздел лицензии.

