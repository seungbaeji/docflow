from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProcessResult:
    document_type: str
    success: bool
    parsed_data: dict[str, object] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
