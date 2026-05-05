from dataclasses import dataclass


@dataclass(frozen=True)
class EcmDocument:
    document_id: str
    name: str
    content_type: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class SapRecord:
    document_id: str
    company_code: str
    fiscal_year: int
    status: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class OcrPage:
    page_number: int
    text: str
    confidence: float
    metadata: dict[str, object]


@dataclass(frozen=True)
class StoredObject:
    location: str
    content_type: str
    size_bytes: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class ProcessingRecord:
    record_id: str
    status: str
    artifact_refs: list[str]
    metadata: dict[str, object]


@dataclass(frozen=True)
class VectorStoreDocument:
    document_id: str
    text: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class VectorSearchHit:
    document_id: str
    score: float
    metadata: dict[str, object]


@dataclass(frozen=True)
class QueueMessage:
    message_id: str
    topic: str
    payload: dict[str, object]
    metadata: dict[str, object]
