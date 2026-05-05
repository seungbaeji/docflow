from __future__ import annotations

from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.types.boundary.external import QueueMessage, WorkflowRunRecord


class WorkflowRuntime:
    def __init__(
        self,
        *,
        workflow_run_store: WorkflowRunStore | None = None,
        workflow_queue: WorkflowQueuePort | None = None,
    ) -> None:
        self.workflow_run_store = workflow_run_store
        self.workflow_queue = workflow_queue


def save_workflow_run(
    runtime: WorkflowRuntime,
    *,
    record_id: str,
    status: str,
    artifact_refs: list[str],
    metadata: dict[str, object],
) -> None:
    if runtime.workflow_run_store is None:
        return
    runtime.workflow_run_store.save_workflow_run(
        WorkflowRunRecord(
            record_id=record_id,
            status=status,
            artifact_refs=artifact_refs,
            metadata=metadata,
        )
    )


def enqueue_workflow_message(
    runtime: WorkflowRuntime,
    *,
    message_id: str,
    topic: str,
    payload: dict[str, object],
    metadata: dict[str, object],
) -> None:
    if runtime.workflow_queue is None:
        return
    runtime.workflow_queue.enqueue(
        QueueMessage(
            message_id=message_id,
            topic=topic,
            payload=payload,
            metadata=metadata,
        )
    )
