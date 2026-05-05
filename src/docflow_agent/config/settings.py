"""Application settings."""

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    name: str = "docflow-agent"
    title: str = "Document Processing Service"
    env: Literal["local", "test", "prod"] = "local"
    debug: bool = False


class ApiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    public_base_url: str = "http://127.0.0.1:8000"


class UiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8501


class LlmSettings(BaseModel):
    provider: Literal["stub", "openai", "gemini"] = "stub"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    api_key: SecretStr | None = None
    base_url: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0
    retry_backoff_multiplier: float = 2.0
    retry_on_rate_limit: bool = True


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    ui: UiSettings = Field(default_factory=UiSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)

    model_config = SettingsConfigDict(
        env_prefix="DOCFLOW_AGENT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def app_name(self) -> str:
        return self.app.name

    @property
    def api_title(self) -> str:
        return self.app.title

    @property
    def llm_provider(self) -> Literal["stub", "openai", "gemini"]:
        return self.llm.provider

    @property
    def llm_model(self) -> str:
        return self.llm.model

    @property
    def llm_temperature(self) -> float:
        return self.llm.temperature

    def get_llm_api_key(self) -> SecretStr | None:
        return self.llm.api_key

    def get_llm_base_url(self) -> str | None:
        return self.llm.base_url


def _resolve_env_file(env_file: str | None = None) -> str:
    return env_file or os.environ.get("DOCFLOW_AGENT_ENV_FILE") or ".env"


@lru_cache(maxsize=None)
def _get_settings_cached(env_file: str) -> Settings:
    return Settings(_env_file=env_file)  # type: ignore[call-arg]


def get_settings(env_file: str | None = None) -> Settings:
    return _get_settings_cached(_resolve_env_file(env_file))


def load_settings(
    *,
    env_file: str | None = None,
    api_host: str | None = None,
    api_port: int | None = None,
    api_reload: bool | None = None,
    api_public_base_url: str | None = None,
    ui_host: str | None = None,
    ui_port: int | None = None,
) -> Settings:
    settings = get_settings(env_file).model_copy(deep=True)

    if (
        api_host is not None
        or api_port is not None
        or api_reload is not None
        or api_public_base_url is not None
    ):
        settings.api = settings.api.model_copy(
            update={
                "host": api_host if api_host is not None else settings.api.host,
                "port": api_port if api_port is not None else settings.api.port,
                "reload": api_reload if api_reload is not None else settings.api.reload,
                "public_base_url": (
                    api_public_base_url
                    if api_public_base_url is not None
                    else settings.api.public_base_url
                ),
            }
        )

    if ui_host is not None or ui_port is not None:
        settings.ui = settings.ui.model_copy(
            update={
                "host": ui_host if ui_host is not None else settings.ui.host,
                "port": ui_port if ui_port is not None else settings.ui.port,
            }
        )

    return settings
