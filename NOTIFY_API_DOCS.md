# Документация API уведомлений о продаже автомобилей

## Описание

API для управления уведомлениями о продаже новых автомобилей. Использует Redis для хранения уведомлений и FastAPI в качестве веб-фреймворка.

Базовый URL: `/v1/notify`

---

## Эндпоинты

### 1. Добавить уведомление

**POST** `/v1/notify/`

Добавляет новое уведомление о продаже автомобиля в очередь Redis. Операция выполняется атомарно с использованием распределенной блокировки.

#### Параметры запроса (JSON Body)

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `advert_url` | string (URL) | Да | URL объявления о продаже автомобиля |
| `analytics` | string | Да | Аналитическая информация в текстовом виде |
| `seller_phone` | string (Phone) | Да | Номер телефона продавца (формат E.164) |

#### Ответ (200 OK)

```json
{
  "success": true,
  "message": "Уведомление успешно добавлено"
}
```

#### Примеры использования с aiohttp

```python
import aiohttp
import asyncio

async def add_notification():
    url = "http://localhost:8000/v1/notify/"
    
    payload = {
        "advert_url": "https://example.com/car/123",
        "analytics": "Популярная модель, хорошая цена",
        "seller_phone": "+79991234567"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Успех: {data['message']}")
            else:
                print(f"Ошибка: {response.status}")
                print(await response.text())

# Запуск
asyncio.run(add_notification())
```

#### Возможные ошибки

- `422 Unprocessable Entity` - ошибка валидации входных данных
- `500 Internal Server Error` - ошибка Redis или блокировки

---

### 2. Получить все уведомления

**GET** `/v1/notify/`

Возвращает список всех накопленных уведомлений и **автоматически очищает их из Redis**. После вызова этого эндпоинта список уведомлений будет пуст.

#### Параметры запроса

Нет параметров.

#### Ответ (200 OK)

```json
{
  "data": [
    {
      "advert_url": "https://example.com/car/123",
      "analytics": "Популярная модель, хорошая цена",
      "seller_phone": "+79991234567"
    },
    {
      "advert_url": "https://example.com/car/456",
      "analytics": "Срочная продажа, отличное состояние",
      "seller_phone": "+79997654321"
    }
  ]
}
```

Если уведомлений нет:

```json
{
  "data": []
}
```

#### Примеры использования с aiohttp

**Простой вариант:**

```python
import aiohttp
import asyncio

async def get_notifications():
    url = "http://localhost:8000/v1/notify/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                notifications = data['data']
                print(f"Получено уведомлений: {len(notifications)}")
                for notify in notifications:
                    print(f"- {notify['advert_url']} | {notify['seller_phone']}")
            else:
                print(f"Ошибка: {response.status}")

# Запуск
asyncio.run(get_notifications())
```

**Расширенный вариант с обработкой:**

```python
import aiohttp
import asyncio
from typing import List, Dict

async def fetch_and_process_notifications():
    url = "http://localhost:8000/v1/notify/"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                result = await response.json()
                
                notifications: List[Dict] = result.get('data', [])
                
                if not notifications:
                    print("Нет новых уведомлений")
                    return []
                
                print(f"Обработка {len(notifications)} уведомлений...")
                
                for idx, notify in enumerate(notifications, 1):
                    print(f"\n[{idx}] Новое объявление:")
                    print(f"  URL: {notify['advert_url']}")
                    print(f"  Аналитика: {notify['analytics']}")
                    print(f"  Телефон: {notify['seller_phone']}")
                
                return notifications
                
        except aiohttp.ClientError as e:
            print(f"Ошибка соединения: {e}")
            return []
        except asyncio.TimeoutError:
            print("Превышено время ожидания")
            return []

# Запуск
asyncio.run(fetch_and_process_notifications())
```

#### Особенности

- **Деструктивная операция**: После получения уведомлений они удаляются из Redis
- **Максимальное количество**: До 100 уведомлений за один запрос
- **Атомарность**: Операция выполняется с распределенной блокировкой

#### Возможные ошибки

- `500 Internal Server Error` - ошибка Redis или повреждение данных

---

## Полный пример использования

```python
import aiohttp
import asyncio
from typing import List, Dict

class NotificationClient:
    """Клиент для работы с API уведомлений"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.notify_url = f"{base_url}/v1/notify/"
    
    async def add_notification(self, advert_url: str, analytics: str, seller_phone: str) -> bool:
        """Добавить новое уведомление"""
        payload = {
            "advert_url": advert_url,
            "analytics": analytics,
            "seller_phone": seller_phone
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.notify_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('success', False)
                return False
    
    async def get_all_notifications(self) -> List[Dict]:
        """Получить все уведомления (с очисткой)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.notify_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                return []


async def main():
    client = NotificationClient()
    
    # Добавление уведомлений
    print("Добавление уведомлений...")
    success1 = await client.add_notification(
        advert_url="https://auto.ru/cars/used/sale/123456789",
        analytics="Toyota Camry 2020, отличное состояние, один владелец",
        seller_phone="+79991234567"
    )
    print(f"Уведомление 1: {'добавлено' if success1 else 'ошибка'}")
    
    success2 = await client.add_notification(
        advert_url="https://auto.ru/cars/used/sale/987654321",
        analytics="BMW X5 2019, полная комплектация, срочная продажа",
        seller_phone="+79997654321"
    )
    print(f"Уведомление 2: {'добавлено' if success2 else 'ошибка'}")
    
    # Получение уведомлений
    print("\nПолучение уведомлений...")
    notifications = await client.get_all_notifications()
    print(f"Получено: {len(notifications)} уведомлений")
    
    for notify in notifications:
        print(f"\n  URL: {notify['advert_url']}")
        print(f"  Аналитика: {notify['analytics']}")
        print(f"  Телефон: {notify['seller_phone']}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Требования

Для работы с API необходимо установить:

```bash
pip install aiohttp
```

Для валидации данных на стороне клиента (опционально):

```bash
pip install pydantic pydantic-extra-types
```

---

## Примечания

1. **Формат телефона**: Номер телефона должен быть в международном формате (например, `+79991234567`)
2. **Валидация URL**: `advert_url` должен быть валидным HTTP/HTTPS URL
3. **Очистка данных**: GET-запрос к `/v1/notify/` удаляет все полученные уведомления
4. **Конкурентность**: Все операции защищены распределенной блокировкой Redis
5. **Ограничения**: Максимум 100 уведомлений за один GET-запрос

---

## Дополнительные эндпоинты

Для проверки работоспособности API используйте:

- **GET** `/v1/lifecheck` - проверка состояния сервиса
