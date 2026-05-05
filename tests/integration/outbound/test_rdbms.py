import pytest

from docflow_agent.errors import DatabaseIntegrationError
from docflow_agent.outbound.testing.rdbms import InMemoryWorkflowRunStore
from docflow_agent.types.boundary.external import WorkflowRunRecord


def test_save_and_load_workflow_run() -> None:
    store = InMemoryWorkflowRunStore()
    record = WorkflowRunRecord(
        record_id="run-001",
        status="completed",
        artifact_refs=["source-001", "bundle-001"],
        metadata={"flow": "document_process"},
    )

    store.save_workflow_run(record)

    assert store.load_workflow_run("run-001") == record


def test_find_workflow_runs_filters_by_status() -> None:
    store = InMemoryWorkflowRunStore()
    store.save_workflow_run(
        WorkflowRunRecord(
            record_id="run-001",
            status="completed",
            artifact_refs=[],
            metadata={},
        )
    )
    store.save_workflow_run(
        WorkflowRunRecord(
            record_id="run-002",
            status="pending",
            artifact_refs=[],
            metadata={},
        )
    )

    records = store.find_workflow_runs(status="pending")

    assert [record.record_id for record in records] == ["run-002"]


def test_load_workflow_run_raises_for_missing_record() -> None:
    with pytest.raises(DatabaseIntegrationError, match="run-missing"):
        InMemoryWorkflowRunStore().load_workflow_run("run-missing")
