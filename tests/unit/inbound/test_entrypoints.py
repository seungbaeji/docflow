import os
import sys
from pathlib import Path

import pytest

from docflow_agent.config.settings import load_settings
import docflow_agent.entrypoints.api as api_entrypoint
import docflow_agent.entrypoints.ui as ui_entrypoint


def test_load_settings_reads_custom_env_file_and_overrides(tmp_path: Path) -> None:
    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "\n".join(
            [
                "DOCFLOW_AGENT_API__HOST=127.0.0.1",
                "DOCFLOW_AGENT_API__PORT=8100",
                "DOCFLOW_AGENT_UI__HOST=127.0.0.1",
                "DOCFLOW_AGENT_UI__PORT=8600",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(
        env_file=str(env_file),
        api_host="0.0.0.0",
        api_port=9100,
        ui_port=8700,
    )

    assert settings.api.host == "0.0.0.0"
    assert settings.api.port == 9100
    assert settings.ui.host == "127.0.0.1"
    assert settings.ui.port == 8700


def test_api_entrypoint_passes_runtime_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / "api.env"
    env_file.write_text("DOCFLOW_AGENT_API__RELOAD=false\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(app: object, *, host: str, port: int, reload: bool) -> None:
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr("docflow_agent.entrypoints.api.uvicorn.run", fake_run)

    api_entrypoint.main(
        [
            "--env-file",
            str(env_file),
            "--host",
            "0.0.0.0",
            "--port",
            "9100",
            "--reload",
        ]
    )

    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9100
    assert captured["reload"] is True
    assert captured["app"] is not None


def test_ui_entrypoint_passes_runtime_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / "ui.env"
    env_file.write_text("", encoding="utf-8")

    monkeypatch.delenv("DOCFLOW_AGENT_ENV_FILE", raising=False)
    monkeypatch.delenv("DOCFLOW_AGENT_API__PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr("docflow_agent.entrypoints.ui.streamlit_cli.main", lambda: 0)

    with pytest.raises(SystemExit) as exc_info:
        ui_entrypoint.main(
            [
                "--env-file",
                str(env_file),
                "--host",
                "0.0.0.0",
                "--port",
                "8600",
                "--api-base-url",
                "http://127.0.0.1:9100",
            ]
        )

    assert exc_info.value.code == 0
    assert os.environ["DOCFLOW_AGENT_ENV_FILE"] == str(env_file)
    assert os.environ["DOCFLOW_AGENT_API__PUBLIC_BASE_URL"] == "http://127.0.0.1:9100"
    assert sys.argv[0:6] == [
        "streamlit",
        "run",
        str(Path(ui_entrypoint.__file__).resolve().parents[1] / "inbound" / "ui" / "streamlit_app.py"),
        "--server.address",
        "0.0.0.0",
        "--server.port",
    ]
    assert sys.argv[6] == "8600"
