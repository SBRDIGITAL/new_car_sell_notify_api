# Redis Streams для уведомлений: простое руководство

Это пошаговая, дружелюбная для новичков инструкция, как подключить Redis Streams к вашему проекту FastAPI, чтобы принимать уведомления (producer) и отдавать их по запросу Telegram-бота (polling). 

Важно: В этой версии архитектуры НЕТ отдельного воркера, который сам пушит в Telegram. Бот периодически (каждые N секунд) опрашивает ваш FastAPI эндпоинт. FastAPI читает накопленные уведомления из Stream и после успешной выдачи очищает пул (удаляет сообщения).

Фокус: минимальная архитектура, быстрое поднятие окружения на Windows, понятные примеры кода и частые ошибки.

---

## Что мы строим

- Producer: ваш FastAPI (`/v1/notify/`) принимает уведомление и записывает его в Redis Stream.
- Broker: Redis Streams хранит события/уведомления в потоке.
- Polling-endpoint: бот каждые N секунд вызывает эндпоинт (например `/v1/notify/pull`) и получает ВСЕ непрочитанные уведомления.
- После выдачи уведомлений FastAPI очищает поток (либо удаляет выданные сообщения, либо полностью триммит поток).

Графически:

FastAPI (producer) → Redis Stream → (бот опрашивает FastAPI) → FastAPI возвращает уведомления и очищает поток

---

## Почему именно Redis Streams

- Простая установка (один сервис Redis).
- Поддержка consumer groups: несколько обработчиков без потерь.
- Есть блокирующее чтение (XREAD/BLOCK) и подтверждение обработки (XACK).
- Хорошо подходит для «сначала сделаем просто и надёжно», можно масштабировать.

Альтернатива: RabbitMQ — мощнее по маршрутизации, но сложнее. Для вашего кейса Streams быстрее в работе.

---

## Установка Redis на Windows

На Windows самый простой и стабильный вариант — Docker Desktop.

### Вариант A: Docker Desktop (рекомендуется)

1) Установите Docker Desktop (перезагрузка/включите WSL2 при необходимости).
2) В терминале (bash.exe) выполните:

```bash
# скачать образ
docker pull redis:7-alpine

# запустить контейнер Redis (порт 6379)
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

Опционально: сохранять данные на диск (персистентность) и задать пароль:

```bash
docker run -d --name redis \
  -p 6379:6379 \
  -v "$PWD/redis-data":/data \
  redis:7-alpine \
  redis-server --appendonly yes --requirepass "YOUR_STRONG_PASSWORD"
```

Подключение с паролем потребует указать его в клиенте (см. примеры ниже).

### Вариант B: WSL2 (Ubuntu)

Внутри WSL-распределения:

```bash
sudo apt update
sudo apt install -y redis-server
# запустить и проверить
sudo service redis-server start
redis-cli ping
```

### Быстрый тест

```bash
# ping
redis-cli ping
# добавить сообщение в stream
a) XADD new_car_notify_stream * data "{\"msg\":\"hello\"}"
# прочитать
b) XREAD COUNT 1 STREAMS new_car_notify_stream 0-0
```

Если видите ответ с вашим сообщением — всё работает.

---

## Python зависимости

Добавьте библиотеку клиента Redis:

- Если используете requirements.txt — добавьте строку `redis>=5.0.0` и выполните установку:

```bash
python -m pip install -r requirements.txt
```

- Либо точечно:

```bash
python -m pip install "redis>=5.0.0"
```

Библиотека `redis` поддерживает и синхронный, и асинхронный API. Мы будем использовать `redis.asyncio`.

---

## Схема данных уведомления

В проекте уже есть модель `NewCarNotify` (`app/api/v1/schemas/notify.py`):
- advert_url: HttpUrl
- analytics: str
- seller_phone: PhoneNumber

Пример JSON:

```json
{
  "advert_url": "https://example.com/adv/123",
  "analytics": "Новая продажа: цена X, регион Y",
  "seller_phone": "+7 999 111-22-33"
}
```

---

## Producer: запись в Stream из FastAPI

Ниже — пример того, как в вашем роуте сохранять событие в Redis Stream. Это не меняет публичный контракт API — вы, как и раньше, принимаете JSON от клиента.

```python
# app/api/v1/routes/notify.py
import json
import redis.asyncio as redis
from fastapi import APIRouter
from ..schemas.notify import NewCarNotify

router = APIRouter(prefix="/notify")

# Для dev окружения — хардкодим параметры; в проде положите в .env
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
# Если задавали пароль у Redis: r = redis.Redis(host="localhost", port=6379, password="YOUR_STRONG_PASSWORD", decode_responses=True)

@router.post("/")
async def waiting_notify(advert: NewCarNotify):
    payload = advert.model_dump()
    msg_id = await r.xadd("new_car_notify_stream", {"data": json.dumps(payload, ensure_ascii=False)})
    # Можно вернуть ID события и сам payload
    return {"id": msg_id, **payload}
```

Ключи:
- `XADD` — добавляет запись в поток; клиентская обёртка — `xadd`.
- Мы сохраняем сериализованный JSON в поле `data`.

---

## Pull-модель: бот опрашивает FastAPI и очищает поток

Вместо отдельного воркера мы реализуем один эндпоинт, который:
1. Читает все сообщения из потока (XRANGE или XREAD).
2. Возвращает их боту.
3. Очищает поток (удаляет именно выданные сообщения или полностью триммит).

Есть два подхода к очистке:

1) Полный сброс после чтения (просто XTRIM до 0):
   - Проще всего: прочитали — отдали — обнулили.
   - Минус: нет истории вообще.

2) Точное удаление прочитанных (XDEL по id каждой записи):
   - Более «аккуратно», но операция может быть чуть тяжелее при большом объёме.

Для начала используем вариант №1 (XTRIM ~ 0) — минимальная логика.

Пример эндпоинта `pull`:

```python
# app/api/v1/routes/notify.py (фрагмент)
import json
from fastapi import HTTPException

@router.get("/pull")
async def pull_all():
  """Забирает ВСЕ текущие уведомления и очищает поток."""
  stream_key = "new_car_notify_stream"
  # Читаем ВСЮ историю (осторожно: если сообщений много). Для старта ок.
  entries = await r.xrange(stream_key, min='-', max='+')
  if not entries:
    return {"notifications": []}
  notifications = []
  for msg_id, fields in entries:
    data_raw = fields.get("data")
    if data_raw:
      try:
        notifications.append(json.loads(data_raw))
      except json.JSONDecodeError:
        notifications.append({"_error": "bad_json", "raw": data_raw})
  # Очищаем поток (полный трим). Можно trim до 0 или XTRIM <count>.
  # Полный сброс:
  await r.xtrim(stream_key, maxlen=0, approximate=False)
  return {"notifications": notifications, "count": len(notifications)}
```

Вариант с точечным удалением (замена блока очистки):

```python
  # Вместо полного трима:
  for msg_id, _ in entries:
    await r.xdel(stream_key, msg_id)
```

Выбор зависит от того, нужна ли история. Если историю хотите оставить и лишь «помечать прочитанное», вместо удаления можно переносить записи в другой поток или сохранять в БД.

Оптимизация на будущее: добавить параметр `limit` / пагинацию, если сообщений станет много.

---

## Telegram-бот: схема опроса

1. Бот раз в N секунд делает HTTP GET `/v1/notify/pull`.
2. Если `notifications` пустой — бот ничего не делает.
3. Если список не пуст — бот отправляет их пользователю, больше не повторяет эти же уведомления (так как поток очищен).

Почему очистку делаем на стороне FastAPI:
- Централизация логики.
- Можно добавить аудит/логирование.
- Можно легко сменить стратегию (сохранять историю в БД) без изменения кода бота.

---

## Docker Compose (удобно для dev)

Минимальный `docker-compose.yml` (по желанию):

```yaml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - ./redis-data:/data
    command: ["redis-server", "--appendonly", "yes"]
```

Запуск:

```bash
docker compose up -d
```

---

## Тестирование end-to-end (локально)

1) Redis запущен (контейнер/WSL).  
2) Запустите FastAPI (uvicorn):

```bash
uvicorn main:app --reload
```

3) Отправьте тестовое уведомление:

```bash
curl -X POST http://127.0.0.1:8000/v1/notify/ \
  -H "Content-Type: application/json" \
  -d '{
    "advert_url": "https://example.com/adv/123",
    "analytics": "Новая продажа: цена X, регион Y",
    "seller_phone": "+7 999 111-22-33"
  }'
```

4) Вызовите эндпоинт pull и убедитесь, что сообщения возвращаются, а повторный вызов даёт пустой список:

```bash
curl http://127.0.0.1:8000/v1/notify/pull
```

Если вернулся `{"notifications": [...], "count": N}` — после второго вызова должен быть `{"notifications": [], "count": 0}`.

---

## Частые ошибки и как их исправить

- `Error: Connection refused` — контейнер Redis не запущен или порт 6379 занят. Проверьте `docker ps`, порт и firewall.
- Аутентификация: если задали `--requirepass`, укажите `password=...` при создании клиента `Redis`.
- `ResponseError: BUSYGROUP` при создании группы — группа уже есть. Поймайте исключение и игнорируйте (как в примере).
- Кодировка: используйте `decode_responses=True`, чтобы получать строки, а не bytes.
- Не вижу сообщения в воркере: проверьте, что читаете id `">"` и что группа создана с `id="$"` (чтобы брать новые записи). Для чтения старой истории используйте XRANGE/`0-0`.

---

## Минимальные «правила больших пальцев»

- Один поток (stream) на тип события — просто и понятно.
- Если выбираете трим — убедитесь, что не теряете нужную историю.
- Если выбираете XDEL — следите за производительностью при большом числе сообщений.
- Для продакшена включите персистентность (AOF) и настройте резервное копирование.
- Не открывайте Redis наружу без пароля/шифрования. В dev — ок, в prod — настройте безопасность.
- Для продакшена включите персистентность (AOF) и настройте резервное копирование.
- Не открывайте Redis наружу без пароля/шифрования. В dev — ок, в prod — настройте безопасность.

---

## Дальнейшие шаги для проекта

- Добавить зависимость `redis` в `requirements.txt`.
- Внедрить запись в Stream в `app/api/v1/routes/notify.py`.
- Реализовать эндпоинт `/v1/notify/pull` (poll + очистка).
- (Опционально) Добавить параметр `limit`, пагинацию, сохранение истории в БД.
- Добавить `docker-compose.yml` для Redis.
- Дополнить README.md краткой инструкцией запуска.
- Покрыть базовыми тестами (lifecheck и POST /v1/notify) и, по возможности, интеграционным тестом воркера (можно замокать Redis).

Если нужно — могу автоматически добавить пример кода и compose-файл в репозиторий.
