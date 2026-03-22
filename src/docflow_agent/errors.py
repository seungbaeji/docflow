"""Application error definitions."""


class DocflowError(Exception):
    """Base error for explicit workflow failures."""


class ProcessingError(DocflowError):
    """Base error for source processing failures."""


class UnsupportedSourceKindError(ProcessingError):
    def __init__(self, source_kind: str) -> None:
        super().__init__(f"Unsupported source kind: {source_kind}")
        self.source_kind = source_kind


class UnsupportedCategoryError(ProcessingError):
    def __init__(self, category: str) -> None:
        super().__init__(f"Unsupported category: {category}")
        self.category = category


class OutboundError(DocflowError):
    """Base error for outbound integration failures."""


class EcmError(OutboundError):
    """Base error for ECM integration failures."""


class EcmRequestError(EcmError):
    def __init__(self, method: str, path: str, reason: str) -> None:
        super().__init__(f"ECM request failed: {method} {path} ({reason})")
        self.method = method
        self.path = path
        self.reason = reason


class EcmResponseError(EcmError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"ECM response handling failed: {path} ({reason})")
        self.path = path
        self.reason = reason


class MailIntegrationError(OutboundError):
    def __init__(self, message_id: str) -> None:
        super().__init__(f"Mail integration is not implemented for message_id={message_id}")
        self.message_id = message_id


class LlmError(OutboundError):
    """Base error for LLM integration failures."""


class UnsupportedLlmProviderError(LlmError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Unsupported LLM provider: {provider}")
        self.provider = provider
