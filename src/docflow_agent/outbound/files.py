from docflow_agent.types.common import FileInfo
from docflow_agent.types.documents import SpreadsheetFile


def load_spreadsheet(file_info: FileInfo) -> SpreadsheetFile:
    # Stub file loading with deterministic sheet names for local testing.
    return SpreadsheetFile(
        file_info=file_info,
        sheets=["Invoice", "LineItems", "Summary"],
    )
