from docflow_agent.core.category.invoice import categorize_excel_units
from docflow_agent.types.unit import ExcelSheetUnit


def test_categorize_excel_units_detects_invoice() -> None:
    category = categorize_excel_units(
        [
            ExcelSheetUnit(sheet_name="Invoice", row_count=10),
            ExcelSheetUnit(sheet_name="LineItems", row_count=10),
            ExcelSheetUnit(sheet_name="Summary", row_count=10),
        ]
    )

    assert category == "invoice"
