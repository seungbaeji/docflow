from collections.abc import Sequence
from typing import Protocol

from docflow_agent.types.value.chat import ChatTurn


class DocumentLlmPort(Protocol):
    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        ...

    def summarize_document(
        self,
        payload: dict[str, object],
    ) -> str:
        ...

    def ask_document_question(
        self,
        question: str,
        payload: dict[str, object],
    ) -> str:
        ...
