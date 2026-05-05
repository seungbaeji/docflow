from docflow_agent.core.rules.invoice import apply_invoice_rule
from docflow_agent.types.bundle import InvoiceBundle
from docflow_agent.types.unit import ExcelSheetUnit


def test_apply_invoice_rule_marks_invoice_bundle() -> None:
    bundle = InvoiceBundle(
        category="invoice",
        source_name="invoice.xlsx",
        units=[
            ExcelSheetUnit(sheet_name="Invoice", row_count=10),
            ExcelSheetUnit(sheet_name="LineItems", row_count=10),
        ],
    )

    result = apply_invoice_rule(bundle)

    assert result.metadata["invoice_rule_applied"] is True
    assert result.invoice_number == "INV-001"
