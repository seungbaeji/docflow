from docflow_agent.types.bundle import InvoiceBundle


def validate_accounting_rule(bundle: InvoiceBundle) -> list[str]:
    errors: list[str] = []

    if not bundle.invoice_number:
        errors.append("Missing invoice number.")

    if len(bundle.units) < 2:
        errors.append("Invoice bundle must contain at least two units.")

    return errors
