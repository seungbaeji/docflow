from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExcelSheetUnit:
    sheet_name: str
    row_count: int
    metadata: dict[str, object] = field(default_factory=dict)
