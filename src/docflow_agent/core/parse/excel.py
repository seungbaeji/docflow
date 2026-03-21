from docflow_agent.types.documents import SpreadsheetFile


def parse_excel_sheet_names(document: SpreadsheetFile) -> dict[str, object]:
    return {
        "file_name": document.file_info.name,
        "sheet_names": list(document.sheets),
        "sheet_count": len(document.sheets),
    }
