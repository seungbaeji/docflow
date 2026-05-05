from __future__ import annotations

from docflow_agent.errors import SapIntegrationError
from docflow_agent.types.boundary.external import SapRecord


class SapClient:
    def __init__(self, records_by_document: dict[str, list[SapRecord]] | None = None) -> None:
        self.records_by_document = dict(records_by_document or {})


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
