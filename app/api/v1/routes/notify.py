"""Модуль для работы с уведомлениями `API`.
"""

from fastapi import APIRouter

from ..schemas.notify import NewCarNotify


router = APIRouter(prefix='/notify')



@router.post("/")
async def wating_notify(advert: NewCarNotify):
    return advert.model_dump()