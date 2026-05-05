"""Generic outbound integration errors."""

from docflow_agent.errors.base import DocflowError


class OutboundError(DocflowError):
    """Base error for outbound integration failures."""


class MailIntegrationError(OutboundError):
    def __init__(self, message_id: str) -> None:
        super().__init__(f"Mail integration is not implemented for message_id={message_id}")
        self.message_id = message_id


class SapIntegrationError(OutboundError):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"SAP integration could not find document_id={document_id}")
        self.document_id = document_id


class OcrIntegrationError(OutboundError):
    def __init__(self, file_name: str) -> None:
        super().__init__(f"OCR integration could not extract text from file={file_name}")
        self.file_name = file_name


class MissingPdfDependencyError(OutboundError):
    def __init__(self, dependency_name: str) -> None:
        super().__init__(
            f"PDF integration requires optional dependency={dependency_name}. "
            'Install it with: uv sync --extra pdf'
        )
        self.dependency_name = dependency_name


class PdfIntegrationError(OutboundError):
    def __init__(self, file_name: str, reason: str | None = None) -> None:
        detail = f"PDF integration could not parse file={file_name}"
        if reason:
            detail = f"{detail}: {reason}"
        super().__init__(detail)
        self.file_name = file_name
        self.reason = reason


class StorageIntegrationError(OutboundError):
    def __init__(self, location: str) -> None:
        super().__init__(f"Storage integration failed for location={location}")
        self.location = location


class DatabaseIntegrationError(OutboundError):
    def __init__(self, record_id: str) -> None:
        super().__init__(f"Database integration could not find record_id={record_id}")
        self.record_id = record_id
