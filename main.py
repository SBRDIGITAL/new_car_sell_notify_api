"""Главный модуль приложения `FastAPI` для `API` уведомлений о продаже новых автомобилей.

Этот модуль инициализирует и настраивает приложение `FastAPI`, включая регистрацию
роутеров и управление жизненным циклом приложения.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter

from app.api.v1.routes.lifecheck import router as lifecheck_router
from app.api.v1.routes.notify import router as notify_router
from app.config.config_reader import env_config



class FastAPIapp:
    """
    ## Класс для инициализации и настройки `FastAPI` приложения.

    Управляет созданием экземпляра `FastAPI`, регистрацией роутеров и 
    жизненным циклом приложения.

    Attributes:
        app (FastAPI): Экземпляр приложения `FastAPI`.
        app_routers (dict[str, list[APIRouter]]): Словарь роутеров, где ключ - префикс,
            а значение - список роутеров для этого префикса.
    """

    def __init__(self):
        """
        ## Инициализирует экземпляр класса.
        """
        self.app = self._create_app()
        self.app_routers: dict[str, list[APIRouter]] = {
            '/v1': [
                lifecheck_router,
                notify_router,
                # more routers ...
            ]
        }
        self.__post_init()

    def __post_init(self):
        """ ## Выполняет пост-инициализацию после создания экземпляра класса. """
        self._inlude_routers()

    def _create_app(self) -> FastAPI:
        """
        ## Создает и настраивает экземпляр FastAPI приложения.
        
        В зависимости от окружения (production/development) настраивает
        параметры безопасности и доступности документации.
        
        Returns:
            FastAPI: Настроенный экземпляр приложения FastAPI.
        """
        is_production = env_config.env.lower() == "production"
        
        return FastAPI(
            lifespan=self.lifespan,
            # Отключаем документацию и отладочные функции в production
            docs_url=None if is_production else "/docs",
            redoc_url=None if is_production else "/redoc",
            openapi_url=None if is_production else "/openapi.json",
            # Отключаем отображение деталей ошибок в production
            debug=not is_production,
        )

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """
        ## Управляет жизненным циклом приложения `FastAPI`.

        Контекстный менеджер для выполнения действий при запуске и остановке приложения.

        Args:
            app (FastAPI): Экземпляр приложения `FastAPI`.

        Yields:
            None: Контроль передается приложению во время его работы.
        """
        # До запуска приложения
        # print('До запуска')
        yield  # Приложение работает
        # Выключение приложения
        # print('После запуска')

    def _inlude_routers(self):
        """
        ## Регистрирует все роутеры в приложении `FastAPI`.

        Проходит по словарю `app_routers` и включает каждый роутер
            с соответствующим префиксом.

        Raises:
            ValueError: Если `self.app` не является экземпляром `FastAPI`.
        """
        if not isinstance(self.app, FastAPI):
            raise ValueError('Не передан объект FastAPI приложения')
        for i in self.app_routers.items():
            [self.app.include_router(r, prefix=i[0]) for r in i[-1]]


fastapi_app = FastAPIapp()
app: FastAPI = fastapi_app.app


# Запуск при разработке
# uvicorn main:app --reload