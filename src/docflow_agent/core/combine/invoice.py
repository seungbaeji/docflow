from docflow_agent.types.value.bundle import InvoiceBundle
from docflow_agent.types.value.source import SpreadsheetSource
from docflow_agent.types.value.unit import ExcelSheetUnit


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
