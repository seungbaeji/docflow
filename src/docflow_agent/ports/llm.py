from typing import Protocol


class DocumentLlmPort(Protocol):
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

