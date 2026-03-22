from docflow_agent.types.source import SpreadsheetSource
from docflow_agent.types.unit import ExcelSheetUnit


def parse_excel_units(source: SpreadsheetSource) -> list[ExcelSheetUnit]:
    return [
        ExcelSheetUnit(
            sheet_name=sheet_name,
            row_count=10,
            metadata={"source_name": source.source_ref.name},
        )
        for sheet_name in source.sheet_names
    ]
