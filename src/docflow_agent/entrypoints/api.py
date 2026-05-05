from __future__ import annotations

import uvicorn

from docflow_agent.bootstrap import get_container
from docflow_agent.config.settings import get_settings


def main() -> None:
    get_container()
    settings = get_settings()
    uvicorn.run(
        "docflow_agent.inbound.api.server:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
    )
