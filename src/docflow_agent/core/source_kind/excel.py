from docflow_agent.types.source import SpreadsheetSource


def is_excel_source(source: SpreadsheetSource) -> bool:
    return source.source_ref.content_type in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }
