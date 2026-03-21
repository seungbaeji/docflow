def apply_invoice_rule(parsed_data: dict[str, object]) -> dict[str, object]:
    raw_sheet_names = parsed_data.get("sheet_names", [])
    sheet_names = raw_sheet_names if isinstance(raw_sheet_names, list) else []
    has_invoice_sheet = any(sheet_name == "Invoice" for sheet_name in sheet_names)
    return {
        **parsed_data,
        "invoice_number": "INV-001" if has_invoice_sheet else None,
        "invoice_rule_applied": has_invoice_sheet,
    }
