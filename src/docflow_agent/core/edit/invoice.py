from docflow_agent.types.bundle import InvoiceBundle
from docflow_agent.types.edit import CellValueEditIntent


def build_invoice_edit_intents(bundle: InvoiceBundle) -> list[CellValueEditIntent]:
    if bundle.invoice_number is None:
        return []

    return [
        CellValueEditIntent(
            sheet_name="Summary",
            cell_ref="B2",
            value=bundle.invoice_number,
        )
    ]
