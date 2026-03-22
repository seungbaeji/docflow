from docflow_agent.core.source_kind.excel import is_excel_source
from docflow_agent.types.source import SpreadsheetSource


def detect_source_kind(source: SpreadsheetSource) -> str:
    if is_excel_source(source):
        return "excel"
    return "unknown"
