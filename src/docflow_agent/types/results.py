from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProcessResult:
    source_kind: str
    category: str
    success: bool
    unit_count: int = 0
    bundle_data: dict[str, object] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
