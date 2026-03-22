from docflow_agent.settings import Settings, get_settings


def get_dev_summary(settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    return f"{active_settings.app_name} development helpers are available via FastAPI and Streamlit."


def get_architecture_summary() -> str:
    return "Dependencies: inbound -> usecases, usecases -> core, usecases -> outbound"
