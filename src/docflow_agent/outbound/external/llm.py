import json
import re
import time
from collections.abc import Sequence
from importlib import import_module

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from docflow_agent.errors import (
    LlmQuotaExceededError,
    LlmRateLimitError,
    LlmRequestError,
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedLlmProviderError,
)
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.settings import Settings, get_settings
from docflow_agent.types.value.chat import ChatTurn


class LlmClient:
    def __init__(
        self,
        chat_model: BaseChatModel,
        provider: str = "unknown",
        max_retries: int = 0,
        retry_backoff_seconds: float = 0.0,
        retry_backoff_multiplier: float = 1.0,
        retry_on_rate_limit: bool = True,
    ) -> None:
        self.chat_model = chat_model
        self.provider = provider
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.retry_backoff_multiplier = retry_backoff_multiplier
        self.retry_on_rate_limit = retry_on_rate_limit


class ExternalDocumentLlmGateway(DocumentLlmPort):
    def __init__(self, client: LlmClient | None = None) -> None:
        self._client = client

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        return chat_text(
            message=message,
            system_prompt=system_prompt,
            history=history,
            client=self._client,
        )

    def summarize_document(
        self,
        payload: dict[str, object],
    ) -> str:
        return summarize_document(payload=payload, client=self._client)

    def ask_document_question(
        self,
        question: str,
        payload: dict[str, object],
    ) -> str:
        return ask_document_question(question=question, payload=payload, client=self._client)


def build_llm_client(settings: Settings | None = None) -> LlmClient:
    active_settings = settings or get_settings()
    llm_settings = active_settings.llm
    api_key = llm_settings.api_key

    if llm_settings.provider == "stub":
        return LlmClient(
            FakeListChatModel(
                responses=[
                    "Stub summary: document analysis is running in local test mode.",
                ]
            ),
            provider="stub",
            max_retries=llm_settings.max_retries,
            retry_backoff_seconds=llm_settings.retry_backoff_seconds,
            retry_backoff_multiplier=llm_settings.retry_backoff_multiplier,
            retry_on_rate_limit=llm_settings.retry_on_rate_limit,
        )

    if llm_settings.provider == "openai":
        if api_key is None:
            raise MissingLlmApiKeyError("openai")
        try:
            chat_openai_module = import_module("langchain_openai")
        except ImportError as exc:
            raise MissingLlmDependencyError("openai", "langchain-openai") from exc

        return LlmClient(
            chat_openai_module.ChatOpenAI(
                model=llm_settings.model,
                temperature=llm_settings.temperature,
                api_key=api_key,
                base_url=llm_settings.base_url,
                timeout=llm_settings.timeout_seconds,
                max_retries=llm_settings.max_retries,
            ),
            provider="openai",
            max_retries=llm_settings.max_retries,
            retry_backoff_seconds=llm_settings.retry_backoff_seconds,
            retry_backoff_multiplier=llm_settings.retry_backoff_multiplier,
            retry_on_rate_limit=llm_settings.retry_on_rate_limit,
        )

    if llm_settings.provider == "gemini":
        if api_key is None:
            raise MissingLlmApiKeyError("gemini")
        try:
            google_genai_module = import_module("langchain_google_genai")
        except ImportError as exc:
            raise MissingLlmDependencyError("gemini", "langchain-google-genai") from exc

        return LlmClient(
            google_genai_module.ChatGoogleGenerativeAI(
                model=llm_settings.model,
                temperature=llm_settings.temperature,
                google_api_key=api_key.get_secret_value(),
                timeout=llm_settings.timeout_seconds,
                max_retries=llm_settings.max_retries,
            ),
            provider="gemini",
            max_retries=llm_settings.max_retries,
            retry_backoff_seconds=llm_settings.retry_backoff_seconds,
            retry_backoff_multiplier=llm_settings.retry_backoff_multiplier,
            retry_on_rate_limit=llm_settings.retry_on_rate_limit,
        )

    raise UnsupportedLlmProviderError(llm_settings.provider)


def summarize_document(
    payload: dict[str, object],
    client: LlmClient | None = None,
) -> str:
    active_client = client or build_llm_client()
    return _invoke_text(
        [
            SystemMessage(
                content=(
                    "You summarize document-processing context for an internal document agent. "
                    "Be concise and focus on document type, important fields, and next actions."
                )
            ),
            HumanMessage(
                content="Summarize this document payload:\n"
                + json.dumps(payload, ensure_ascii=True, sort_keys=True)
            ),
        ],
        client=active_client,
    )


def chat_text(
    message: str,
    system_prompt: str | None = None,
    history: Sequence[ChatTurn] | None = None,
    client: LlmClient | None = None,
) -> str:
    active_client = client or build_llm_client()
    messages: list[SystemMessage | HumanMessage | AIMessage] = []
    if system_prompt is not None:
        messages.append(SystemMessage(content=system_prompt))
    for turn in history or []:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))
    messages.append(HumanMessage(content=message))
    return _invoke_text(messages, client=active_client)


def ask_document_question(
    question: str,
    payload: dict[str, object],
    client: LlmClient | None = None,
) -> str:
    active_client = client or build_llm_client()
    return _invoke_text(
        [
            SystemMessage(
                content=(
                    "You answer questions about document-processing payloads. "
                    "Use only the provided payload and say when information is missing."
                )
            ),
            HumanMessage(
                content=(
                    f"Question: {question}\n"
                    f"Payload: {json.dumps(payload, ensure_ascii=True, sort_keys=True)}"
                )
            ),
        ],
        client=active_client,
    )


def _invoke_text(
    messages: list[SystemMessage | HumanMessage | AIMessage],
    client: LlmClient,
) -> str:
    backoff_seconds = client.retry_backoff_seconds
    for attempt in range(client.max_retries + 1):
        try:
            response = client.chat_model.invoke(messages)
        except Exception as exc:  # pragma: no cover - provider-specific failures
            classified_error = _classify_llm_error(provider=client.provider, exc=exc)
            if not _should_retry(classified_error, client=client, attempt=attempt):
                raise classified_error from exc
            sleep_seconds = _resolve_sleep_seconds(classified_error, backoff_seconds)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            backoff_seconds *= client.retry_backoff_multiplier
            continue
        return _message_to_text(response.content)
    raise AssertionError("unreachable")


def _message_to_text(content: str | list[str | dict[str, object]]) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        text = item.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts)


def _classify_llm_error(provider: str, exc: Exception) -> LlmRequestError:
    reason = str(exc)
    retry_after_seconds = _extract_retry_after_seconds(reason)
    lowered_reason = reason.lower()

    if "quota exceeded" in lowered_reason or "quota exhausted" in lowered_reason:
        return LlmQuotaExceededError(
            provider=provider,
            reason=reason,
            retry_after_seconds=retry_after_seconds,
        )
    if "rate limit" in lowered_reason or "resource_exhausted" in lowered_reason:
        return LlmRateLimitError(
            provider=provider,
            reason=reason,
            retry_after_seconds=retry_after_seconds,
        )
    return LlmRequestError(provider=provider, reason=reason)


def _extract_retry_after_seconds(reason: str) -> float | None:
    please_retry_match = re.search(r"Please retry in ([0-9]+(?:\\.[0-9]+)?)s", reason)
    if please_retry_match is not None:
        return float(please_retry_match.group(1))

    retry_delay_match = re.search(r"'retryDelay': '([0-9]+)s'", reason)
    if retry_delay_match is not None:
        return float(retry_delay_match.group(1))

    return None


def _should_retry(
    error: LlmRequestError,
    client: LlmClient,
    attempt: int,
) -> bool:
    if attempt >= client.max_retries:
        return False
    if isinstance(error, LlmQuotaExceededError):
        return False
    if isinstance(error, LlmRateLimitError):
        return client.retry_on_rate_limit
    return False


def _resolve_sleep_seconds(
    error: LlmRequestError,
    backoff_seconds: float,
) -> float:
    if isinstance(error, LlmRateLimitError) and error.retry_after_seconds is not None:
        return error.retry_after_seconds
    return backoff_seconds
