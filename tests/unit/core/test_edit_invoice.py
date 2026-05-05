from docflow_agent.core.edit.invoice import build_invoice_edit_intents
from docflow_agent.types.bundle import InvoiceBundle
from docflow_agent.types.unit import ExcelSheetUnit


def test_build_invoice_edit_intents_returns_summary_update() -> None:
    bundle = InvoiceBundle(
        category="invoice",
        source_name="invoice.xlsx",
        units=[
            ExcelSheetUnit(sheet_name="Invoice", row_count=10),
            ExcelSheetUnit(sheet_name="Summary", row_count=5),
        ],
        invoice_number="INV-001",
    )

    edit_intents = build_invoice_edit_intents(bundle)

    assert len(edit_intents) == 1
    assert edit_intents[0].sheet_name == "Summary"
    assert edit_intents[0].cell_ref == "B2"
    assert edit_intents[0].value == "INV-001"
