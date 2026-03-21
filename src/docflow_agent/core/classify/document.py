from docflow_agent.core.classify.excel import is_excel_invoice
from docflow_agent.types.documents import SpreadsheetFile


def classify_document(document: SpreadsheetFile) -> str:
    if is_excel_invoice(document):
        return "excel_invoice"
    return "unknown"
