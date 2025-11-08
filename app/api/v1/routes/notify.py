"""Модуль для работы с уведомлениями `API`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ...dependencies.redis import get_notifications_manager

from ..schemas.notify import NewCarNotify, NewCarNotifyListResponse, NewCarNotifyResponse

from ...service.redis.new_notifications import NewNotificationsManager



router = APIRouter(prefix='/notify', tags=['notifications', 'v1'])



@router.post("/", response_model=NewCarNotifyResponse)
async def waiting_notify(
    advert: NewCarNotify,
    notifications_manager: Annotated[
        NewNotificationsManager,
        Depends(get_notifications_manager)
    ],
):
    """
    ## Добавить новое уведомление о продаже автомобиля.
    
    Принимает данные об объявлении и добавляет уведомление в очередь Redis.
    Операция выполняется атомарно с использованием распределенной блокировки.
    
    Args:
        advert (NewCarNotify): Данные уведомления, содержащие:
            - advert_url: URL объявления о продаже
            - analytics: Аналитическая информация в текстовом виде
            - seller_phone: Номер телефона продавца
        notifications_manager (NewNotificationsManager): Менеджер уведомлений (внедряется через DI).
    
    Returns:
        NewCarNotifyResponse: Объект ответа с полями:
            - success (bool): True при успешном добавлении
            - message (str): Информационное сообщение
    
    Raises:
        HTTPException: При ошибках валидации входных данных
        redis.exceptions.LockError: Если не удалось получить блокировку
        redis.exceptions.RedisError: При ошибках взаимодействия с Redis
    
    Example:
        ```json
        POST /v1/notify/
        {
            "advert_url": "https://example.com/car/123",
            "analytics": "Популярная модель, хорошая цена",
            "seller_phone": "+79991234567"
        }
        ```
    """
    payload: dict = advert.model_dump(mode='json')
    await notifications_manager.add_notification(payload)
    return NewCarNotifyResponse(success=True)


@router.get("/", response_model=NewCarNotifyListResponse)
async def get_notifications(
    notifications_manager: Annotated[
        NewNotificationsManager,
        Depends(get_notifications_manager)
    ],
):
    """
    ## Получить все уведомления о продаже автомобилей.
    
    Возвращает список всех накопленных уведомлений и автоматически очищает их из Redis.
    После вызова этого эндпоинта список уведомлений будет пуст.
    Операция выполняется атомарно с использованием распределенной блокировки.
    
    Args:
        notifications_manager (NewNotificationsManager): Менеджер уведомлений (внедряется через DI).
    
    Returns:
        NewCarNotifyListResponse: Объект ответа содержащий:
            - data (list[NewCarNotify]): Список уведомлений. Пустой список, если уведомлений нет.
    
    Raises:
        redis.exceptions.LockError: Если не удалось получить блокировку
        redis.exceptions.RedisError: При ошибках взаимодействия с Redis
        json.JSONDecodeError: Если данные в Redis повреждены
    
    Note:
        - После успешного вызова все полученные уведомления удаляются из Redis
        - Блокировка гарантирует, что во время получения не будут добавлены новые уведомления
        - Максимальное количество возвращаемых уведомлений: 100
    
    Example:
        ```json
        GET /v1/notify/
        Response:
        {
            "data": [
                {
                    "advert_url": "https://example.com/car/123",
                    "analytics": "Популярная модель",
                    "seller_phone": "+79991234567"
                }
            ]
        }
        ```
    """
    notifications = await notifications_manager.get_notifications()
    return NewCarNotifyListResponse(data=notifications)