"""Application settings."""

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


class LlmSettings(BaseModel):
    provider: Literal["stub", "openai", "gemini"] = "stub"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    api_key: SecretStr | None = None
    base_url: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
