from docflow_agent.settings import get_settings


def main() -> None:
    settings = get_settings()
    print(f"{settings.app_name} development helpers are available via FastAPI and Streamlit.")
