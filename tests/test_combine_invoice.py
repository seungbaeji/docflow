from docflow_agent.core.combine.invoice import combine_invoice_units
from docflow_agent.types.source import SourceRef, SpreadsheetSource
from docflow_agent.types.unit import ExcelSheetUnit


def test_combine_invoice_units_creates_invoice_bundle() -> None:
    source = SpreadsheetSource(
        source_ref=SourceRef(
            name="invoice.xlsx",
            location="stub://fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        ),
        sheet_names=["Invoice", "LineItems"],
    )

    bundle = combine_invoice_units(
        source=source,
        units=[
            ExcelSheetUnit(sheet_name="Invoice", row_count=10),
            ExcelSheetUnit(sheet_name="LineItems", row_count=10),
        ],
        category="invoice",
    )

    assert bundle.category == "invoice"
    assert bundle.source_name == "invoice.xlsx"
    assert bundle.metadata["unit_count"] == 2
