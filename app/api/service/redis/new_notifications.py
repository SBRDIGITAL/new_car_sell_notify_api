import json

from redis.asyncio.client import Redis

from .redis_client import redis_client



class NewNotificationsManager:
    """
    ## Менеджер для управления уведомлениями о новых автомобилях в Redis.
    
    Класс предоставляет потокобезопасные методы для добавления и получения уведомлений
    с использованием Redis Lists и распределенных блокировок.
    
    Attributes:
        redis (Redis): Клиент Redis для асинхронных операций.
        list_key (str): Ключ Redis для хранения списка уведомлений.
        lock_key (str): Ключ Redis для распределенной блокировки.
    
    Examples:
        >>> manager = NewNotificationsManager(redis_client)
        >>> await manager.add_notification({"advert_url": "https://...", "analytics": "..."})
        >>> notifications = await manager.get_notifications()
    """

    def __init__(self, redis: Redis):
        """
        ## Инициализация менеджера уведомлений.
        
        Args:
            redis (Redis): Экземпляр асинхронного клиента Redis.
        """
        self.redis = redis
        self.list_key = "car_notifications_list"
        self.lock_key = "car_notifications_lock"

    async def __clear_notifications(self):
        """
        ## Приватный метод для очистки списка уведомлений.
        
        Удаляет ключ со списком уведомлений из Redis.
        Метод вызывается только внутри блокировки в get_notifications.
        """
        await self.redis.delete(self.list_key)
    
    async def add_notification(self, notification: dict):
        """
        ## Добавляет уведомление в список Redis с распределенной блокировкой.
        
        Метод сериализует уведомление в JSON и добавляет его в начало списка Redis.
        Использует распределенную блокировку для предотвращения race conditions.
        
        Args:
            notification (dict): Словарь с данными уведомления.
                Должен содержать ключи: advert_url, analytics, seller_phone.
        
        Raises:
            redis.exceptions.LockError: Если не удалось получить блокировку за 10 секунд.
            redis.exceptions.RedisError: При ошибках взаимодействия с Redis.
        
        Note:
            - Блокировка автоматически освобождается через 5 секунд (timeout).
            - Максимальное время ожидания блокировки - 10 секунд (blocking_timeout).
        """
        async with self.redis.lock(self.lock_key, timeout=5, blocking_timeout=10):
            notification_json = json.dumps(notification, ensure_ascii=False)
            await self.redis.lpush(self.list_key, notification_json)

    async def get_notifications(self, count: int = 100) -> list[dict]:
        """
        ## Получает список уведомлений из Redis и атомарно очищает список.
        
        Метод читает указанное количество уведомлений, десериализует их из JSON
        и полностью очищает список в Redis. Все операции выполняются атомарно
        под распределенной блокировкой.
        
        Args:
            count (int, optional): Максимальное количество уведомлений для получения.
                По умолчанию 100.
        
        Returns:
            list[dict]: Список словарей с данными уведомлений. Возвращает пустой список,
                если уведомлений нет.
        
        Raises:
            redis.exceptions.LockError: Если не удалось получить блокировку за 10 секунд.
            redis.exceptions.RedisError: При ошибках взаимодействия с Redis.
            json.JSONDecodeError: Если данные в Redis повреждены и не могут быть десериализованы.
        
        Note:
            - После вызова метода список уведомлений в Redis будет очищен.
            - Блокировка гарантирует, что во время чтения и очистки не будут добавлены новые уведомления.
        """
        async with self.redis.lock(self.lock_key, timeout=5, blocking_timeout=10):
            notifications_raw = await self.redis.lrange(self.list_key, 0, count - 1)
            notifications = [json.loads(n) for n in notifications_raw]
            await self.__clear_notifications()
            return notifications


new_notifications_manager = NewNotificationsManager(redis_client)