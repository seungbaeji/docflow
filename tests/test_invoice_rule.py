from docflow_agent.core.rules.invoice import apply_invoice_rule


def test_apply_invoice_rule_marks_invoice_data() -> None:
    parsed_data = {"sheet_names": ["Invoice", "LineItems"], "sheet_count": 2}

    result = apply_invoice_rule(parsed_data)

    assert result["invoice_rule_applied"] is True
    assert result["invoice_number"] == "INV-001"
