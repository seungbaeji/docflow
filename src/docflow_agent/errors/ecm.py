"""ECM-specific integration errors."""

from docflow_agent.errors.outbound import OutboundError


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
