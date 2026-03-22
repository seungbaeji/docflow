from docflow_agent.types.bundle import InvoiceBundle
from docflow_agent.types.source import SpreadsheetSource
from docflow_agent.types.unit import ExcelSheetUnit


def combine_invoice_units(
    source: SpreadsheetSource,
    units: list[ExcelSheetUnit],
    category: str,
) -> InvoiceBundle:
    return InvoiceBundle(
        category=category,
        source_name=source.source_ref.name,
        units=units,
        metadata={
            "sheet_names": [unit.sheet_name for unit in units],
            "unit_count": len(units),
        },
    )
