"""Application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "docflow-agent"
    api_title: str = "Document Processing Service"
    llm_provider: str = "stub"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="DOCFLOW_AGENT_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
