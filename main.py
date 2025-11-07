from typing import Union
from contextlib import asynccontextmanager

from fastapi import FastAPI



@asynccontextmanager
async def lifespan(app: FastAPI):
    # До запуска приложения
    # print('До запуска')
    yield  # Приложение работает
    # Выключение приложения
    # print('После запуска')

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}