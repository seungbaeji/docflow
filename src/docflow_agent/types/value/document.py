from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class UploadPayload:
    upload_id: str
    file_name: str
    stored_path: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class SourcePayload:
    prompt: str
    source_type: Literal["pdf", "excel", "generic"]
    file_path: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    uploaded: bool = False


@dataclass(frozen=True)
class ParsedDocumentPayload:
    file_name: str
    page_count: int = 0
    markdown: str | None = None
    text: str | None = None


@dataclass(frozen=True)
class ParsedUnitPayload:
    name: str
    prompt: str
    page_number: int | None = None
    content: str | None = None
    element_count: int | None = None


@dataclass(frozen=True)
class CategorizedUnitPayload:
    name: str
    prompt: str
    category: str
    page_number: int | None = None
    content: str | None = None
    element_count: int | None = None


@dataclass(frozen=True)
class BundlePayload:
    category: str
    unit_ref_ids: list[str] = field(default_factory=list)
    source_ref_id: str | None = None


@dataclass(frozen=True)
class AnalysisPayload:
    bundle_ref_id: str
    unit_count: int
    category: str


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


@dataclass(frozen=True)
class DocumentQuestionPayload:
    question: str
    document: DocumentPayload


@dataclass(frozen=True)
class DatasetPayload:
    records: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class MailDraftPayload:
    recipients: list[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""


@dataclass(frozen=True)
class MailResultPayload:
    draft_ref_id: str | None
    status: Literal["sent", "rejected"]
