from typing import Any

from pydantic import Field

from docflow_agent.types.boundary.base import BoundaryModel


class EcmDocument(BoundaryModel):
    document_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EcmSearchResponse(BoundaryModel):
    items: list[EcmDocument] = Field(default_factory=list)


class EcmUploadResponse(BoundaryModel):
    document_id: str = Field(min_length=1)
    name: str | None = None
    content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SapRecord(BoundaryModel):
    document_id: str = Field(min_length=1)
    company_code: str = Field(min_length=1)
    fiscal_year: int = Field(ge=1)
    status: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OcrPage(BoundaryModel):
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PdfElement(BoundaryModel):
    element_type: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    content: str | None = None
    bounding_box: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PdfDocument(BoundaryModel):
    file_name: str = Field(min_length=1)
    page_count: int = Field(ge=0)
    markdown: str | None = None
    html: str | None = None
    text: str | None = None
    elements: list[PdfElement] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_json: dict[str, Any] = Field(default_factory=dict)


class StoredObject(BoundaryModel):
    location: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunRecord(BoundaryModel):
    record_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    artifact_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorStoreDocument(BoundaryModel):
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchHit(BoundaryModel):
    document_id: str = Field(min_length=1)
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueueMessage(BoundaryModel):
    message_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
