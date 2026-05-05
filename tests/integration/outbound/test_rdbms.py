import pytest

from docflow_agent.errors import DatabaseIntegrationError
from docflow_agent.outbound.testing.rdbms import InMemoryProcessingRecordStore
from docflow_agent.types.boundary.external import ProcessingRecord


def test_save_and_load_processing_record() -> None:
    store = InMemoryProcessingRecordStore()
    record = ProcessingRecord(
        record_id="run-001",
        status="completed",
        artifact_refs=["source-001", "bundle-001"],
        metadata={"flow": "document_process"},
    )

    store.save_processing_record(record)

    assert store.load_processing_record("run-001") == record


def test_find_processing_records_filters_by_status() -> None:
    store = InMemoryProcessingRecordStore()
    store.save_processing_record(
        ProcessingRecord(
            record_id="run-001",
            status="completed",
            artifact_refs=[],
            metadata={},
        )
    )
    store.save_processing_record(
        ProcessingRecord(
            record_id="run-002",
            status="pending",
            artifact_refs=[],
            metadata={},
        )
    )

    records = store.find_processing_records(status="pending")

    assert [record.record_id for record in records] == ["run-002"]


def test_load_processing_record_raises_for_missing_record() -> None:
    with pytest.raises(DatabaseIntegrationError, match="run-missing"):
        InMemoryProcessingRecordStore().load_processing_record("run-missing")
