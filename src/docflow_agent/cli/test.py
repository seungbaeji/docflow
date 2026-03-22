from docflow_agent.types.source import SourceRef
from docflow_agent.usecases.process_source import process_source


def main() -> None:
    result = process_source(
        SourceRef(
            name="invoice.xlsx",
            location="stub://fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        )
    )
    print(result)
