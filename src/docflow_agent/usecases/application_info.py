def get_dev_summary(app_name: str) -> str:
    return f"{app_name} development helpers are available via FastAPI and Streamlit."


def get_architecture_summary() -> str:
    return "Dependencies: inbound -> usecases, usecases -> core, usecases -> outbound"
