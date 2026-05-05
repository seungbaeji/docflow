"""Application error exports."""

from docflow_agent.errors.base import DocflowError
from docflow_agent.errors.ecm import EcmError, EcmRequestError, EcmResponseError
from docflow_agent.errors.llm import (
    LlmError,
    LlmQuotaExceededError,
    LlmRateLimitError,
    LlmRequestError,
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedLlmProviderError,
)
from docflow_agent.errors.outbound import (
    DatabaseIntegrationError,
    EmptyPdfOutputError,
    MailIntegrationError,
    MissingPdfDependencyError,
    OcrIntegrationError,
    OutboundError,
    PdfIntegrationError,
    SapIntegrationError,
    StorageIntegrationError,
)
from docflow_agent.errors.processing import (
    DocumentAgentRuntimeError,
    ProcessingError,
    UnsupportedCategoryError,
    UnsupportedSourceKindError,
)

__all__ = [
    "DatabaseIntegrationError",
    "DocumentAgentRuntimeError",
    "DocflowError",
    "EmptyPdfOutputError",
    "EcmError",
    "EcmRequestError",
    "EcmResponseError",
    "LlmError",
    "LlmQuotaExceededError",
    "LlmRateLimitError",
    "LlmRequestError",
    "MailIntegrationError",
    "MissingLlmApiKeyError",
    "MissingLlmDependencyError",
    "MissingPdfDependencyError",
    "OcrIntegrationError",
    "OutboundError",
    "PdfIntegrationError",
    "ProcessingError",
    "SapIntegrationError",
    "StorageIntegrationError",
    "UnsupportedCategoryError",
    "UnsupportedLlmProviderError",
    "UnsupportedSourceKindError",
]
