from dataclasses import dataclass, field

from docflow_agent.ports.llm import DocumentLlmPort


@dataclass
class StubDocumentLlmGateway(DocumentLlmPort):
    summary_response: str = "Stub summary"
    answer_response: str = "Stub answer"
    summarized_payloads: list[dict[str, object]] = field(default_factory=list)
    asked_questions: list[tuple[str, dict[str, object]]] = field(default_factory=list)

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

