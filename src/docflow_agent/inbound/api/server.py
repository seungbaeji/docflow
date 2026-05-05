from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from docflow_agent.bootstrap import AppContainer
from docflow_agent.config.settings import Settings
from docflow_agent.inbound.api.routes import router


def create_app(*, settings: Settings, container: AppContainer) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container
        yield

    app = FastAPI(title=settings.api_title, lifespan=lifespan)
    app.include_router(router)
    return app
