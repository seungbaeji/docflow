from collections.abc import Sequence
from dataclasses import dataclass, field

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn


@dataclass
class StubDocumentLlmGateway(DocumentLlmPort):
    chat_response: str = "Stub chat response"
    summary_response: str = "Stub summary"
    answer_response: str = "Stub answer"
    chatted_messages: list[tuple[str, str | None, list[ChatTurn]]] = field(default_factory=list)
    summarized_payloads: list[dict[str, object]] = field(default_factory=list)
    asked_questions: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        self.chatted_messages.append((message, system_prompt, list(history or [])))
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
