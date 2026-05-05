"""LLM-specific integration errors."""

from docflow_agent.errors.outbound import OutboundError


class LlmError(OutboundError):
    """Base error for LLM integration failures."""


class UnsupportedLlmProviderError(LlmError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Unsupported LLM provider: {provider}")
        self.provider = provider


class MissingLlmDependencyError(LlmError):
    def __init__(self, provider: str, package_name: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' requires optional dependency '{package_name}'"
        )
        self.provider = provider
        self.package_name = package_name


class MissingLlmApiKeyError(LlmError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Missing API key for LLM provider: {provider}")
        self.provider = provider


class LlmRequestError(LlmError):
    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(f"LLM request failed for provider={provider}: {reason}")
        self.provider = provider
        self.reason = reason


class LlmRateLimitError(LlmRequestError):
    def __init__(
        self,
        provider: str,
        reason: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(provider=provider, reason=reason)
        self.retry_after_seconds = retry_after_seconds


class LlmQuotaExceededError(LlmRateLimitError):
    pass
