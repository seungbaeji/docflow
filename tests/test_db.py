import pytest

from docflow_agent.errors import DatabaseIntegrationError
from docflow_agent.outbound.external.db import (
    DatabaseClient,
    load_processing_record,
    save_processing_record,
)
from docflow_agent.types.external import ProcessingRecord


def test_save_and_load_processing_record() -> None:
    client = DatabaseClient()
    record = ProcessingRecord(
        record_id="run-001",
        status="completed",
        artifact_refs=["source-001", "bundle-001"],
        metadata={"flow": "document_process"},
    )

    save_processing_record(client, record)

    assert load_processing_record(client, "run-001") == record


def test_load_processing_record_raises_for_missing_record() -> None:
    with pytest.raises(DatabaseIntegrationError, match="run-missing"):
        load_processing_record(DatabaseClient(), "run-missing")
