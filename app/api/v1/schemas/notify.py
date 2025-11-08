from pydantic import BaseModel, HttpUrl
from pydantic_extra_types.phone_numbers import PhoneNumber



class NewCarNotify(BaseModel):
    """
    ## Модель уведомления о продаже нового автомобиля.

    Args:
        BaseModel (pydantic.BaseModel): _description_.

    Attributes:
        advert_url (pydantic.HttpUrl): Ссылка на объявление.
        analytics (str): Аналитика о продаже в текстовом виде.
        seller_phone (PhoneNumber): Номер телефона продавца.
    """    
    advert_url: HttpUrl
    analytics: str
    seller_phone: PhoneNumber


class NewCarNotifyResponse(BaseModel):
    """
    ## Модель ответа при успешном добавлении уведомления.

    Attributes:
        success (bool): Статус успешности операции.
        message (str): Сообщение о результате операции.
    """
    success: bool
    message: str = "Уведомление успешно добавлено"


class NewCarNotifyListResponse(BaseModel):
    """
    ## Модель ответа для списка уведомлений о продаже новых автомобилей.

    Args:
        BaseModel (pydantic.BaseModel): _description_.

    Attributes:
        data (list[NewCarNotify]): Список уведомлений о продаже новых автомобилей.
    """    
    data: list[NewCarNotify]