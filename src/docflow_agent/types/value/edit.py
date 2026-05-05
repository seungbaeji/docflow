from dataclasses import dataclass


@dataclass(frozen=True)
class CellValueEditIntent:
    sheet_name: str
    cell_ref: str
    value: str


@dataclass(frozen=True)
class InsertSheetEditIntent:
    sheet_name: str
    position_index: int | None = None


@dataclass(frozen=True)
class RecalculateWorkbookEditIntent:
    full_rebuild: bool = False


@dataclass(frozen=True)
class SaveDocumentEditIntent:
    target_location: str | None = None


@dataclass(frozen=True)
class EditExecutionResult:
    applied_count: int
    strategy: str
