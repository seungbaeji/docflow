from collections.abc import Sequence

from fastapi.testclient import TestClient

from docflow_agent.bootstrap import build_container
from docflow_agent.config.prompt import DEFAULT_CHAT_SYSTEM_PROMPT
from docflow_agent.config.settings import (
    ApiSettings,
    AppSettings,
    LlmSettings,
    Settings,
    UiSettings,
)
from docflow_agent.errors import LlmQuotaExceededError
from docflow_agent.inbound.api.server import create_app
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn


def _settings_without_env() -> Settings:
    return Settings.model_construct(
        app=AppSettings(),
        api=ApiSettings(),
        ui=UiSettings(),
        llm=LlmSettings(),
    )


def test_chat_route_returns_llm_response() -> None:
    llm_gateway = StubDocumentLlmGateway(chat_response="chat ok")
    container = build_container(
        settings=_settings_without_env(),
        llm_gateway=llm_gateway,
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json()["message"] == "chat ok"
    assert isinstance(response.json()["session_id"], str)
    assert llm_gateway.chatted_messages == [("hello", DEFAULT_CHAT_SYSTEM_PROMPT, [])]


def test_chat_route_uses_session_history() -> None:
    llm_gateway = StubDocumentLlmGateway(chat_response="history ok")
    container = build_container(
        settings=_settings_without_env(),
        llm_gateway=llm_gateway,
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        first_response = client.post(
            "/chat",
            json={"message": "hello", "session_id": "session-001"},
        )
        second_response = client.post(
            "/chat",
            json={"message": "next", "session_id": "session-001"},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert llm_gateway.chatted_messages == [
        ("hello", DEFAULT_CHAT_SYSTEM_PROMPT, []),
        (
            "next",
            DEFAULT_CHAT_SYSTEM_PROMPT,
            [
                ChatTurn(role="user", content="hello"),
                ChatTurn(role="assistant", content="history ok"),
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
        raise LlmQuotaExceededError(provider="gemini", reason="quota exhausted")

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
    container = build_container(
        settings=_settings_without_env(),
        llm_gateway=FailingLlmGateway(),
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 429
    assert response.json()["detail"] == "LLM request failed for provider=gemini: quota exhausted"
