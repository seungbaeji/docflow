from docflow_agent.types.common import FileInfo
from docflow_agent.usecases.process_document import process_document


def main() -> None:
    result = process_document(
        FileInfo(
            name="invoice.xlsx",
            path="example/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )
    print(result)


if __name__ == "__main__":
    main()
