from dataclasses import dataclass, field

from docflow_agent.types.value.document import DocumentPayload


@dataclass(frozen=True)
class DocumentAgentToolContext:
    source_ref_id: str
    document_payload: DocumentPayload
    document_summary: str


@dataclass(frozen=True)
class CurrentDocumentMetadataResult:
    source_ref_id: str
    source_type: str
    file_name: str
    file_path: str


@dataclass(frozen=True)
class CurrentDocumentParseResult:
    source_ref_id: str
    page_count: int
    unit_count: int
    parsed_unit_ref_ids: list[str] = field(default_factory=list)
    unit_summaries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CurrentDocumentSummaryResult:
    source_ref_id: str
    summary: str
    source_type: str
    file_name: str
    page_count: int
    unit_count: int
    unit_summaries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CurrentDocumentQuestionResult:
    source_ref_id: str
    question: str
    payload: DocumentPayload


@dataclass(frozen=True)
class DocumentAgentToolTrace:
    tool_name: str
    tool_input_summary: str
    tool_output_summary: str


@dataclass(frozen=True)
class DocumentAgentTrace:
    prompt: str
    tool_calls: list[DocumentAgentToolTrace] = field(default_factory=list)
    final_answer: str | None = None


@dataclass(frozen=True)
class DocumentAgentResult:
    answer: str
    trace: DocumentAgentTrace
