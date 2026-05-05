from dataclasses import dataclass, field

from docflow_agent.errors import DatabaseIntegrationError
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.types.boundary.external import WorkflowRunRecord


@dataclass
class InMemoryWorkflowRunStore(WorkflowRunStore):
    records: dict[str, WorkflowRunRecord] = field(default_factory=dict)

    def save_workflow_run(self, record: WorkflowRunRecord) -> None:
        self.records[record.record_id] = record

    def load_workflow_run(self, record_id: str) -> WorkflowRunRecord:
        record = self.records.get(record_id)
        if record is None:
            raise DatabaseIntegrationError(record_id)
        return record

    def find_workflow_runs(
        self,
        *,
        status: str | None = None,
    ) -> list[WorkflowRunRecord]:
        records = list(self.records.values())
        if status is None:
            return records
        return [record for record in records if record.status == status]
