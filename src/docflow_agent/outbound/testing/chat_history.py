from __future__ import annotations

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory

from docflow_agent.ports.chat_history import ChatHistoryPort


class InMemoryChatHistoryStore(ChatHistoryPort):
    def __init__(self) -> None:
        self.histories: dict[str, InMemoryChatMessageHistory] = {}

    def get(self, session_id: str) -> BaseChatMessageHistory:
        history = self.histories.get(session_id)
        if history is None:
            history = InMemoryChatMessageHistory()
            self.histories[session_id] = history
        return history
