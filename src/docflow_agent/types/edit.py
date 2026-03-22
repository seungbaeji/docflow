from dataclasses import dataclass


@dataclass(frozen=True)
class CellValueEditIntent:
    sheet_name: str
    cell_ref: str
    value: str


@dataclass(frozen=True)
class EditExecutionResult:
    applied_count: int
    strategy: str
