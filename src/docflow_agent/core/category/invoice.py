from docflow_agent.types.unit import ExcelSheetUnit


def categorize_excel_units(units: list[ExcelSheetUnit]) -> str:
    sheet_names = {unit.sheet_name for unit in units}
    if {"Invoice", "LineItems"}.issubset(sheet_names):
        return "invoice"
    return "unknown"
