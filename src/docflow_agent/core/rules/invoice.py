def apply_invoice_rule(parsed_data: dict[str, object]) -> dict[str, object]:
    sheet_names = parsed_data.get("sheet_names", [])
    has_invoice_sheet = "Invoice" in sheet_names
    return {
        **parsed_data,
        "invoice_number": "INV-001" if has_invoice_sheet else None,
        "invoice_rule_applied": has_invoice_sheet,
    }
