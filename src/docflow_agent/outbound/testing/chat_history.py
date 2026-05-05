from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory

from docflow_agent.ports.chat_history import ChatHistoryPort


@dataclass
class InMemoryChatHistoryStore(ChatHistoryPort):
    histories: dict[str, InMemoryChatMessageHistory] = field(default_factory=dict)

    def get(self, session_id: str) -> BaseChatMessageHistory:
        history = self.histories.get(session_id)
        if history is None:
            history = InMemoryChatMessageHistory()
            self.histories[session_id] = history
        return history
