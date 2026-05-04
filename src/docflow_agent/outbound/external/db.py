from __future__ import annotations

from dataclasses import dataclass, field

from docflow_agent.errors import DatabaseIntegrationError
from docflow_agent.types.external import ProcessingRecord


@dataclass
class DatabaseClient:
    records: dict[str, ProcessingRecord] = field(default_factory=dict)


def save_processing_record(client: DatabaseClient, record: ProcessingRecord) -> None:
    client.records[record.record_id] = record


def load_processing_record(client: DatabaseClient, record_id: str) -> ProcessingRecord:
    record = client.records.get(record_id)
    if record is None:
        raise DatabaseIntegrationError(record_id)
    return record

