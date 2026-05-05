from collections.abc import Sequence

from fastapi.testclient import TestClient

from docflow_agent.bootstrap import build_container
from docflow_agent.errors import LlmRequestError
from docflow_agent.inbound.api.server import create_app
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.settings import Settings
from docflow_agent.types.value.chat import ChatTurn


def test_chat_route_returns_llm_response() -> None:
    llm_gateway = StubDocumentLlmGateway(chat_response="chat ok")
    app = create_app()
    app.state.container = build_container(
        settings=Settings(),
        llm_gateway=llm_gateway,
    )
    client = TestClient(app)

    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json()["message"] == "chat ok"
    assert llm_gateway.chatted_messages == [("hello", None, [])]


def test_chat_route_passes_history_and_system_prompt() -> None:
    llm_gateway = StubDocumentLlmGateway(chat_response="history ok")
    app = create_app()
    app.state.container = build_container(
        settings=Settings(),
        llm_gateway=llm_gateway,
    )
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "next",
            "system_prompt": "Be concise.",
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
        },
    )

    assert response.status_code == 200
    assert llm_gateway.chatted_messages == [
        (
            "next",
            "Be concise.",
            [
                ChatTurn(role="user", content="hello"),
                ChatTurn(role="assistant", content="hi"),
            ],
        )
    ]


class FailingLlmGateway(DocumentLlmPort):
    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        raise LlmRequestError(provider="gemini", reason="quota exhausted")

    def summarize_document(
        self,
        payload: dict[str, object],
    ) -> str:
        raise AssertionError("not used in this test")

    def ask_document_question(
        self,
        question: str,
        payload: dict[str, object],
    ) -> str:
        raise AssertionError("not used in this test")


def test_chat_route_translates_llm_failures() -> None:
    app = create_app()
    app.state.container = build_container(
        settings=Settings(),
        llm_gateway=FailingLlmGateway(),
    )
    client = TestClient(app)

    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM request failed for provider=gemini: quota exhausted"
