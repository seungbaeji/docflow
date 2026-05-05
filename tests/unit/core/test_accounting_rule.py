from docflow_agent.core.rules.accounting import validate_accounting_rule
from docflow_agent.types.bundle import InvoiceBundle
from docflow_agent.types.unit import ExcelSheetUnit


def test_validate_accounting_rule_accepts_valid_invoice_bundle() -> None:
    errors = validate_accounting_rule(
        InvoiceBundle(
            category="invoice",
            source_name="invoice.xlsx",
            units=[
                ExcelSheetUnit(sheet_name="Invoice", row_count=10),
                ExcelSheetUnit(sheet_name="LineItems", row_count=10),
                ExcelSheetUnit(sheet_name="Summary", row_count=10),
            ],
            invoice_number="INV-001",
        )
    )

    assert errors == []
