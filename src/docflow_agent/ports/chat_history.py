from typing import Protocol

from langchain_core.chat_history import BaseChatMessageHistory


class ChatHistoryPort(Protocol):
    def get(self, session_id: str) -> BaseChatMessageHistory:
        ...
