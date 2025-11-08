# New Car Sell Notify API

FastAPI-сервис для приема уведомлений о новых объявлениях по продаже автомобилей и выдачи накопленных уведомлений потребителю (например, Telegram-боту). Хранилище — Redis (асинхронный клиент), операции добавления/чтения выполняются атомарно с использованием распределенных блокировок.

- Язык/Runtime: Python 3.12+
- Веб-фреймворк: FastAPI + Starlette
- Валидация: Pydantic v2 (+ pydantic-extra-types для телефонов)
- Хранилище: Redis (через redis.asyncio)
- Конфигурация: pydantic-settings (переменные окружения, .env)
- Запуск: Uvicorn (локально), Docker Compose для Redis


## Кратко о проекте

Сервис предоставляет два основных сценария:

1) Прием уведомления: POST /v1/notify/ — принимает данные объявления (URL, аналитика, телефон продавца) и сохраняет в Redis-список под блокировкой.
2) Выдача и очистка: GET /v1/notify/ — отдаёт список накопленных уведомлений и сразу очищает их в Redis под блокировкой. По умолчанию возвращает до 100 последних записей.

Здоровье сервиса проверяется эндпоинтом GET /v1/lifecheck/.


## Структура репозитория (основное)

- `main.py` — инициализация приложения FastAPI, регистрация роутеров, lifespan.
- `docker-compose.yml` — локальный Redis (порт 6379, без пароля, данные в volume).
- `requirements.txt` — зафиксированные зависимости.
- `pyproject.toml` — метаданные проекта.
- `REDIS_STREAMS_GUIDE.md` — руководство по архитектуре на Redis Streams (альтернативный вариант бэкенда сообщений).
- `тз.md` — краткое ТЗ.

Код приложения:

- `app/api/v1/routes/lifecheck.py` — healthcheck эндпоинт.
- `app/api/v1/routes/notify.py` — приём уведомления (POST) и получение списка (GET).
- `app/api/v1/schemas/notify.py` — Pydantic-схемы запросов/ответов.
- `app/api/dependencies/redis.py` — зависимости FastAPI для DI (Redis-клиент, менеджер уведомлений).
- `app/api/service/redis/redis_client.py` — инициализация асинхронного клиента Redis из настроек.
- `app/api/service/redis/new_notifications.py` — менеджер уведомлений: добавление, атомарное чтение+очистка с блокировкой.
- `app/config/config_reader.py` — pydantic-settings: чтение `.env`/окружения (UTF-8).


## Архитектура и поток данных

- Клиент отправляет уведомление в API: POST /v1/notify/.
- `NewNotificationsManager.add_notification` сериализует данные в JSON и добавляет в Redis-список (`LPUSH`) под распределенной блокировкой.
- Потребитель (бот/сервис) запрашивает GET /v1/notify/.
- `NewNotificationsManager.get_notifications` под блокировкой читает до 100 элементов (`LRANGE`), десериализует и удаляет ключ со списком — тем самым атомарно «забирает и очищает» пул уведомлений.

В `REDIS_STREAMS_GUIDE.md` описана альтернативная реализация на Redis Streams (подойдет, если понадобится история, consumer groups и т.п.). Текущая реализация использует списки для простоты и минимальной задержки.


## API

Базовый префикс версионирования: `/v1`.

Документация Swagger/OpenAPI (при запущенном приложении):
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

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


## Конфигурация

Читается из окружения и `.env` (UTF-8), см. `app/config/config_reader.py`.

Поддерживаемые переменные окружения:

- `REDIS_HOST` (str, по умолчанию `localhost`)
- `REDIS_PORT` (int, по умолчанию `6379`)
- `REDIS_DB` (int, по умолчанию `0`)
- `REDIS_PASSWORD` (str | null, по умолчанию `None`)
- `ENV` (str, по умолчанию `development`)

Пример `.env`:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_password
ENV=development
```


## Запуск локально

Требования: Python 3.12+, Docker (для Redis) — либо установленный Redis любым другим способом.

1) Установить зависимости:

```bash
python -m pip install -r requirements.txt
```

2) Поднять Redis через Docker Compose (из корня репозитория):

```bash
docker compose up -d
```

3) Запустить приложение (из корня репозитория):

```bash
uvicorn main:app --reload
```

Проверить работоспособность:

- http://127.0.0.1:8000/v1/lifecheck/
- http://127.0.0.1:8000/docs


## Примеры запросов (curl)

Добавить уведомление:

```bash
curl -X POST http://127.0.0.1:8000/v1/notify/ \
	-H "Content-Type: application/json" \
	-d '{
		"advert_url": "https://example.com/car/123",
		"analytics": "Популярная модель, хорошая цена",
		"seller_phone": "+7 999 123-45-67"
	}'
```

Получить и очистить уведомления:

```bash
curl http://127.0.0.1:8000/v1/notify/
```


## Технические детали

- Менеджер уведомлений: `app/api/service/redis/new_notifications.py`
	- `add_notification(notification: dict)` — `LPUSH` JSON-строки под блокировкой.
	- `get_notifications(count: int = 100)` — `LRANGE` + очистка ключа под блокировкой.
- Клиент Redis: `app/api/service/redis/redis_client.py` — создается из `env_config`.
- DI-зависимости: `app/api/dependencies/redis.py` — предоставляет клиент и менеджер в роуты.
- Роуты: `app/api/v1/routes/notify.py`, `app/api/v1/routes/lifecheck.py`.


## Дорожная карта / улучшения

- Опционально перейти на Redis Streams (см. `REDIS_STREAMS_GUIDE.md`) для поддержки consumer groups и истории.
- Добавить пагинацию/лимиты в GET `/v1/notify/` (параметры запроса).
- Добавить аутентификацию/авторизацию для эндпоинтов, если сервис выходит наружу.
- Добавить тесты (юнит и интеграционные) и CI.
- Добавить Dockerfile и сервис приложения в `docker-compose.yml` при необходимости контейнеризации API.


## Лицензия

Не указана. При необходимости добавьте файл `LICENSE` и раздел лицензии.

