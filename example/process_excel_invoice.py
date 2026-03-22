from docflow_agent.types.source import SourceRef
from docflow_agent.usecases.process_source import process_source


def main() -> None:
    print("Running example with stubbed source loading. The location below is illustrative only.")
    result = process_source(
        SourceRef(
            name="invoice.xlsx",
            location="stub://example/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        )
    )
    print(result)


if __name__ == "__main__":
    main()
