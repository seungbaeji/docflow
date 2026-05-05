from __future__ import annotations

import argparse
from collections.abc import Sequence

import uvicorn

from docflow_agent.bootstrap import build_container
from docflow_agent.config.settings import load_settings
from docflow_agent.inbound.api.server import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the docflow FastAPI server.")
    parser.add_argument("--env-file", help="Path to the .env file to load.")
    parser.add_argument("--host", help="Host interface to bind the API server to.")
    parser.add_argument("--port", type=int, help="Port to bind the API server to.")
    parser.add_argument(
        "--public-base-url",
        help="Public base URL that UI clients should use for this API.",
    )
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable auto-reload.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    settings = load_settings(
        env_file=args.env_file,
        api_host=args.host,
        api_port=args.port,
        api_reload=args.reload,
        api_public_base_url=args.public_base_url,
    )
    container = build_container(settings=settings)
    app = create_app(settings=settings, container=container)
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
    )
