import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from docflow_agent.errors import UnsupportedLlmProviderError
from docflow_agent.settings import Settings, get_settings


class LlmClient:
    def __init__(self, chat_model: BaseChatModel) -> None:
        self.chat_model = chat_model


def build_llm_client(settings: Settings | None = None) -> LlmClient:
    active_settings = settings or get_settings()

    if active_settings.llm_provider == "stub":
        return LlmClient(
            FakeListChatModel(
                responses=[
                    "Stub summary: document analysis is running in local test mode.",
                ]
            )
        )

    if active_settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return LlmClient(
            ChatOpenAI(
                model=active_settings.llm_model,
                temperature=active_settings.llm_temperature,
                api_key=(
                    SecretStr(active_settings.llm_api_key)
                    if active_settings.llm_api_key is not None
                    else None
                ),
            )
        )

    raise UnsupportedLlmProviderError(active_settings.llm_provider)


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
