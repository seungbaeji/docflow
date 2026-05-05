from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentPayload:
    source_ref_id: str
    source_type: str
    file_name: str
    file_path: str
    page_count: int
    unit_count: int
    unit_summaries: list[str] = field(default_factory=list)
    parsed_unit_ref_ids: list[str] = field(default_factory=list)
    markdown: str | None = None
    text: str | None = None
    markdown_excerpt: str | None = None
    analysis: dict[str, object] | None = None
