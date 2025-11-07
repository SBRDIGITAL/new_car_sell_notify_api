from pydantic import BaseModel, HttpUrl
from pydantic_extra_types.phone_numbers import PhoneNumber



class NewCarNotify(BaseModel):
    """
    ## Модель уведомления о продаже нового автомобиля.

    Args:
        BaseModel (pydantic.BaseModel): _description_.
    """    
    advert_url: HttpUrl
    analytics: str
    seller_phone: PhoneNumber