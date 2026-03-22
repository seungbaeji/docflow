from dataclasses import dataclass, field

from docflow_agent.types.unit import ExcelSheetUnit


@dataclass(frozen=True)
class InvoiceBundle:
    category: str
    source_name: str
    units: list[ExcelSheetUnit]
    invoice_number: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
