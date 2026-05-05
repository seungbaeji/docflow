from typing import Protocol

from docflow_agent.types.boundary.external import WorkflowRunRecord


class WorkflowRunStore(Protocol):
    def save_workflow_run(self, record: WorkflowRunRecord) -> None:
        ...

    def load_workflow_run(self, record_id: str) -> WorkflowRunRecord:
        ...

    def find_workflow_runs(
        self,
        *,
        status: str | None = None,
    ) -> list[WorkflowRunRecord]:
        ...
