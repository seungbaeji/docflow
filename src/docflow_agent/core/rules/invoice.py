from dataclasses import replace

from docflow_agent.types.bundle import InvoiceBundle


def apply_invoice_rule(bundle: InvoiceBundle) -> InvoiceBundle:
    has_invoice_unit = any(unit.sheet_name == "Invoice" for unit in bundle.units)
    return replace(
        bundle,
        invoice_number="INV-001" if has_invoice_unit else None,
        metadata={
            **bundle.metadata,
            "invoice_rule_applied": has_invoice_unit,
        },
    )
