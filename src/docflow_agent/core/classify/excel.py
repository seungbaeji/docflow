from docflow_agent.types.documents import SpreadsheetFile


def is_excel_invoice(document: SpreadsheetFile) -> bool:
    expected_sheets = {"Invoice", "LineItems"}
    return expected_sheets.issubset(set(document.sheets))
