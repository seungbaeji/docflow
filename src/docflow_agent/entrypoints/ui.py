from __future__ import annotations

import sys
from pathlib import Path

from streamlit.web import cli as streamlit_cli


def main() -> None:
    app_path = Path(__file__).resolve().parents[1] / "inbound" / "ui" / "streamlit_app.py"
    sys.argv = ["streamlit", "run", str(app_path)]
    raise SystemExit(streamlit_cli.main())
