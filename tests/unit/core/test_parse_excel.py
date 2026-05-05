from docflow_agent.core.parse.excel import parse_excel_units
from docflow_agent.types.source import SourceRef, SpreadsheetSource


def test_parse_excel_units_returns_sheet_units() -> None:
    source = SpreadsheetSource(
        source_ref=SourceRef(
            name="invoice.xlsx",
            location="stub://fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        ),
        sheet_names=["Invoice", "LineItems", "Summary"],
    )

    units = parse_excel_units(source)

    assert [unit.sheet_name for unit in units] == ["Invoice", "LineItems", "Summary"]
    assert all(unit.row_count == 10 for unit in units)
    assert units[0].metadata["source_name"] == "invoice.xlsx"
