from fastapi import FastAPI

from docflow_agent.bootstrap import get_container
from docflow_agent.inbound.api.routes import router
from docflow_agent.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.api_title)
    app.state.container = get_container()
    app.include_router(router)
    return app


app = create_app()
