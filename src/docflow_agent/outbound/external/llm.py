import json
from collections.abc import Sequence
from importlib import import_module

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from docflow_agent.errors import (
    LlmRequestError,
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedLlmProviderError,
)
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.settings import Settings, get_settings
from docflow_agent.types.value.chat import ChatTurn


class LlmClient:
    def __init__(self, chat_model: BaseChatModel, provider: str = "unknown") -> None:
        self.chat_model = chat_model
        self.provider = provider


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
    try:
        response = client.chat_model.invoke(messages)
    except Exception as exc:  # pragma: no cover - provider-specific failures
        raise LlmRequestError(provider=client.provider, reason=str(exc)) from exc
    return _message_to_text(response.content)


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
