from docflow_agent.settings import get_settings
from docflow_agent.usecases.application_info import get_dev_summary


def main() -> None:
    print(get_dev_summary(get_settings().app_name))
