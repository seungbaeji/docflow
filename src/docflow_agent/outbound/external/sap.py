from __future__ import annotations

from dataclasses import dataclass, field

from docflow_agent.errors import SapIntegrationError
from docflow_agent.types.boundary.external import SapRecord


@dataclass
class SapClient:
    records_by_document: dict[str, list[SapRecord]] = field(default_factory=dict)


def fetch_accounting_records(client: SapClient, document_id: str) -> list[SapRecord]:
    records = client.records_by_document.get(document_id)
    if records is None:
        raise SapIntegrationError(document_id)
    return list(records)


def save_accounting_records(
    client: SapClient,
    document_id: str,
    records: list[SapRecord],
) -> None:
    client.records_by_document[document_id] = list(records)
