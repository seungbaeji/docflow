import argparse

from docflow_agent.types.common import FileInfo
from docflow_agent.usecases.process_document import process_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Process an Excel invoice document.")
    parser.add_argument("path")
    parser.add_argument("--name", default="invoice.xlsx")
    parser.add_argument(
        "--content-type",
        default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    args = parser.parse_args()

    result = process_document(
        FileInfo(name=args.name, path=args.path, content_type=args.content_type)
    )
    print(result)
