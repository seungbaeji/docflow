"""Application settings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "docflow-agent"
    api_title: str = "Document Processing Service"


def get_settings() -> Settings:
    return Settings()
