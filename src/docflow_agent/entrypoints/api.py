from __future__ import annotations

import uvicorn

from docflow_agent.bootstrap import get_container
from docflow_agent.config.settings import get_settings
from docflow_agent.inbound.api.server import create_app


def main() -> None:
    settings = get_settings()
    container = get_container()
    app = create_app(settings=settings, container=container)
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
    )
