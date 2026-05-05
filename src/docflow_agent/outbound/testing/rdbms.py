from dataclasses import dataclass, field

from docflow_agent.errors import DatabaseIntegrationError
from docflow_agent.ports.rdbms import ProcessingRecordPort
from docflow_agent.types.boundary.external import ProcessingRecord


@dataclass
class InMemoryProcessingRecordStore(ProcessingRecordPort):
    records: dict[str, ProcessingRecord] = field(default_factory=dict)

    def save_processing_record(self, record: ProcessingRecord) -> None:
        self.records[record.record_id] = record

    def load_processing_record(self, record_id: str) -> ProcessingRecord:
        record = self.records.get(record_id)
        if record is None:
            raise DatabaseIntegrationError(record_id)
        return record

    def find_processing_records(
        self,
        *,
        status: str | None = None,
    ) -> list[ProcessingRecord]:
        records = list(self.records.values())
        if status is None:
            return records
        return [record for record in records if record.status == status]
