from typing import Protocol

from docflow_agent.types.external import ProcessingRecord


class ProcessingRecordPort(Protocol):
    def save_processing_record(self, record: ProcessingRecord) -> None:
        ...

    def load_processing_record(self, record_id: str) -> ProcessingRecord:
        ...

    def find_processing_records(
        self,
        *,
        status: str | None = None,
    ) -> list[ProcessingRecord]:
        ...

