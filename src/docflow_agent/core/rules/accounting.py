def validate_accounting_rule(parsed_data: dict[str, object]) -> list[str]:
    errors: list[str] = []

    invoice_number = parsed_data.get("invoice_number")
    if not invoice_number:
        errors.append("Missing invoice number.")

    sheet_count = parsed_data.get("sheet_count", 0)
    if not isinstance(sheet_count, int) or sheet_count < 2:
        errors.append("Excel invoice must contain at least two sheets.")

    return errors
