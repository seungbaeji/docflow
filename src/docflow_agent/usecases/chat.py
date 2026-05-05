from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import AIMessage, HumanMessage

from docflow_agent.ports.chat_history import ChatHistoryPort
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn


def respond_in_chat(
    message: str,
    session_id: str,
    *,
    llm_gateway: DocumentLlmPort,
    chat_history_store: ChatHistoryPort,
    system_prompt: str,
    document_context: str | None = None,
) -> str:
    chat_history = chat_history_store.get(session_id)
    active_system_prompt = system_prompt
    if document_context is not None:
        active_system_prompt = (
            f"{active_system_prompt}\n\nCurrent document context:\n{document_context}"
        )
    reply = llm_gateway.chat(
        message=message,
        system_prompt=active_system_prompt,
        history=_to_chat_turns(chat_history.messages),
    )
    chat_history.add_message(HumanMessage(content=message))
    chat_history.add_message(AIMessage(content=reply))
    return reply


def _to_chat_turns(messages: Sequence[object]) -> list[ChatTurn]:
    turns: list[ChatTurn] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            turns.append(ChatTurn(role="user", content=_content_to_text(message.content)))
        elif isinstance(message, AIMessage):
            turns.append(ChatTurn(role="assistant", content=_content_to_text(message.content)))
    return turns


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    return str(content)
