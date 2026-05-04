import json
from importlib import import_module

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from docflow_agent.errors import (
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedLlmProviderError,
)
from docflow_agent.settings import Settings, get_settings


class LlmClient:
    def __init__(self, chat_model: BaseChatModel) -> None:
        self.chat_model = chat_model


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
            )
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
            )
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
            )
        )

    raise UnsupportedLlmProviderError(llm_settings.provider)


def summarize_document(
    payload: dict[str, object],
    client: LlmClient | None = None,
) -> str:
    active_client = client or build_llm_client()
    response = active_client.chat_model.invoke(
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
        ]
    )
    return _message_to_text(response.content)


def ask_document_question(
    question: str,
    payload: dict[str, object],
    client: LlmClient | None = None,
) -> str:
    active_client = client or build_llm_client()
    response = active_client.chat_model.invoke(
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
        ]
    )
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
