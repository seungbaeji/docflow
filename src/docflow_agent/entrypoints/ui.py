from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from streamlit.web import cli as streamlit_cli

from docflow_agent.config.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the docflow Streamlit UI.")
    parser.add_argument("--env-file", help="Path to the .env file to load.")
    parser.add_argument("--host", help="Host interface to bind the UI server to.")
    parser.add_argument("--port", type=int, help="Port to bind the UI server to.")
    parser.add_argument(
        "--api-base-url",
        help="Base URL for the backend chat API that the UI should call.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    settings = load_settings(
        env_file=args.env_file,
        ui_host=args.host,
        ui_port=args.port,
        api_public_base_url=args.api_base_url,
    )

    if args.env_file is not None:
        os.environ["DOCFLOW_AGENT_ENV_FILE"] = args.env_file
    if args.api_base_url is not None:
        os.environ["DOCFLOW_AGENT_API__PUBLIC_BASE_URL"] = args.api_base_url

    app_path = Path(__file__).resolve().parents[1] / "inbound" / "ui" / "streamlit_app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        settings.ui.host,
        "--server.port",
        str(settings.ui.port),
    ]
    raise SystemExit(streamlit_cli.main())
