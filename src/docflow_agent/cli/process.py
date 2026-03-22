import argparse

from docflow_agent.types.source import SourceRef
from docflow_agent.usecases.process_source import process_source


def main() -> None:
    parser = argparse.ArgumentParser(description="Process an Excel source into invoice units/bundles.")
    parser.add_argument("path")
    parser.add_argument("--name", default="invoice.xlsx")
    parser.add_argument("--source-system", default="ecm")
    parser.add_argument(
        "--content-type",
        default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    args = parser.parse_args()

    result = process_source(
        SourceRef(
            name=args.name,
            location=args.path,
            content_type=args.content_type,
            source_system=args.source_system,
        )
    )
    print(result)
