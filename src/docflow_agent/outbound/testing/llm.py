from collections.abc import Sequence

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn


class StubDocumentLlmGateway(DocumentLlmPort):
    def __init__(
        self,
        *,
        chat_response: str = "Stub chat response",
        chat_responses: list[str] | None = None,
        summary_response: str = "Stub summary",
        answer_response: str = "Stub answer",
    ) -> None:
        self.chat_response = chat_response
        self.chat_responses = list(chat_responses or [])
        self.summary_response = summary_response
        self.answer_response = answer_response
        self.chatted_messages: list[tuple[str, str | None, list[ChatTurn]]] = []
        self.summarized_payloads: list[dict[str, object]] = []
        self.asked_questions: list[tuple[str, dict[str, object]]] = []

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        self.chatted_messages.append((message, system_prompt, list(history or [])))
        if self.chat_responses:
            return self.chat_responses.pop(0)
        return self.chat_response

    def summarize_document(
        self,
        payload: dict[str, object],
    ) -> str:
        self.summarized_payloads.append(payload)
        return self.summary_response

    def ask_document_question(
        self,
        question: str,
        payload: dict[str, object],
    ) -> str:
        self.asked_questions.append((question, payload))
        return self.answer_response
