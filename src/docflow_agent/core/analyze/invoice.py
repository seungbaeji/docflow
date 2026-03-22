from docflow_agent.types.bundle import InvoiceBundle


def analyze_invoice_bundle(bundle: InvoiceBundle) -> dict[str, object]:
    return {
        "unit_names": [unit.sheet_name for unit in bundle.units],
        "unit_count": len(bundle.units),
        "source_name": bundle.source_name,
    }
