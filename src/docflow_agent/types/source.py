from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRef:
    name: str
    location: str
    content_type: str
    source_system: str


@dataclass(frozen=True)
class SpreadsheetSource:
    source_ref: SourceRef
    sheet_names: list[str]
