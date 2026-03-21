from docflow_agent.core.rules.accounting import validate_accounting_rule


def test_validate_accounting_rule_accepts_valid_invoice() -> None:
    errors = validate_accounting_rule(
        {
            "invoice_number": "INV-001",
            "sheet_count": 3,
        }
    )

    assert errors == []
