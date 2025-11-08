"""Модуль для проверки работоспособности `API`.

Содержит эндпоинт для проверки доступности и работоспособности сервиса.
"""

from fastapi import APIRouter



router = APIRouter(prefix='/lifecheck', tags=['health', 'v1'])



@router.get("/")
async def check():
    """
    ## Проверяет работоспособность `API`.

    ### Простой эндпоинт для проверки доступности сервиса и подтверждения \
        его корректной работы.

    ### Returns:
        dict: Словарь с ключом `'lifecheck'` и значением `True`, указывающим
            на то, что сервис работает корректно.

    ### Example:
        ```python
            response = await read_root()
            print(response)
            {"lifecheck": True}
        ```
    """
    return {"lifecheck": True}