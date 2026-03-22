from dataclasses import dataclass


@dataclass(frozen=True)
class EcmDocument:
    document_id: str
    name: str
    content_type: str
    metadata: dict[str, object]
