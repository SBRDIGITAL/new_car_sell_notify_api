from redis.asyncio.client import Redis

from ..service.redis.redis_client import redis_client
from ..service.redis.new_notifications import (
    new_notifications_manager,
    NewNotificationsManager
)


async def get_redis_client() -> Redis:
    """
    ## Возвращает клиент `Redis`.

    Returns:
        Redis: Клиент `Redis`.
    """    
    return redis_client


async def get_notifications_manager() -> NewNotificationsManager:
    """
    ## Возвращает объект класса менеджер уведомлений.

    Returns:
        NewNotificationsManager: Менеджер уведомлений.
    """    
    return new_notifications_manager