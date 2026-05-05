from fastapi import FastAPI

from docflow_agent.bootstrap import get_container
from docflow_agent.config.settings import get_settings
from docflow_agent.inbound.api.routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.api_title)
    app.state.container = get_container()
    app.include_router(router)
    return app


app = create_app()
