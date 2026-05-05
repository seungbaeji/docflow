import base64
from collections.abc import Sequence
from pathlib import Path

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
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement
from docflow_agent.types.value.chat import ChatTurn

def _settings_without_env(*, upload_dir: str = "tmp/uploads") -> Settings:
    return Settings.model_construct(
        app=AppSettings(upload_dir=upload_dir),
        api=ApiSettings(),
        ui=UiSettings(),
        llm=LlmSettings(),
    )


def _fake_pdf_parser(client: OpenDataLoaderPdfClient, file_info: FileInfo) -> PdfDocument:
    assert client.format == "markdown,json"
    return PdfDocument(
        file_name=file_info.name,
        page_count=1,
        markdown="# 간이지급명세서\n총지급액: 120000원",
        text="간이지급명세서\n총지급액: 120000원",
        elements=[
            PdfElement(
                element_type="heading",
                page_number=1,
                content="간이지급명세서",
                bounding_box=[72.0, 700.0, 540.0, 730.0],
            ),
            PdfElement(
                element_type="paragraph",
                page_number=1,
                content="총지급액: 120000원",
                bounding_box=[72.0, 640.0, 540.0, 680.0],
            ),
        ],
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


def test_upload_route_saves_file_to_configured_directory(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    container = build_container(
        settings=_settings_without_env(upload_dir=str(upload_dir)),
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        response = client.post(
            "/uploads",
            content=b"%PDF-1.7 fake",
            headers={
                "Content-Type": "application/pdf",
                "X-Filename": "invoice.pdf",
                "X-Session-Id": "session-001",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    stored_path = Path(payload["stored_path"])
    assert payload["session_id"] == "session-001"
    assert payload["file_name"] == "invoice.pdf"
    assert payload["source_ref_id"].startswith("source-")
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == len(b"%PDF-1.7 fake")
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"%PDF-1.7 fake"


def test_upload_route_rejects_missing_filename() -> None:
    container = build_container(
        settings=_settings_without_env(),
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        response = client.post(
            "/uploads",
            content=b"payload",
            headers={"Content-Type": "application/pdf"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload filename is required."


def test_upload_route_accepts_unicode_filename_via_base64_header(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    container = build_container(
        settings=_settings_without_env(upload_dir=str(upload_dir)),
    )
    app = create_app(settings=container.settings, container=container)
    encoded_name = base64.urlsafe_b64encode("정산보고서.pdf".encode("utf-8")).decode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/uploads",
            content=b"%PDF-1.7 fake",
            headers={
                "Content-Type": "application/pdf",
                "X-Filename-Base64": encoded_name,
                "X-Session-Id": "session-kr",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-kr"
    assert payload["file_name"] == "정산보고서.pdf"
    assert Path(payload["stored_path"]).exists()


def test_chat_route_processes_current_uploaded_document(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    llm_gateway = StubDocumentLlmGateway(
        chat_responses=[
            '{"type":"tool_call","tool":"get_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"parse_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"summarize_current_document","arguments":{}}',
            '{"type":"final_answer","answer":"문서 분석 결과: 간이지급명세서이며 총지급액은 120000원입니다."}',
        ]
    )
    container = build_container(
        settings=_settings_without_env(upload_dir=str(upload_dir)),
        llm_gateway=llm_gateway,
        pdf_parser=_fake_pdf_parser,
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        upload_response = client.post(
            "/uploads",
            content=b"%PDF-1.7 fake",
            headers={
                "Content-Type": "application/pdf",
                "X-Filename": "invoice.pdf",
                "X-Session-Id": "session-uploaded-doc",
            },
        )
        chat_response = client.post(
            "/chat",
            json={"message": "해당 문서를 읽고 분석해 줘", "session_id": "session-uploaded-doc"},
        )

    assert upload_response.status_code == 200
    assert chat_response.status_code == 200
    assert chat_response.json()["message"] == "문서 분석 결과: 간이지급명세서이며 총지급액은 120000원입니다."
    assert len(llm_gateway.chatted_messages) == 4


def test_chat_route_answers_question_about_current_uploaded_document(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    llm_gateway = StubDocumentLlmGateway(
        chat_responses=[
            '{"type":"tool_call","tool":"get_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"parse_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"answer_about_current_document","arguments":{"question":"전체 내용을 설명해 줘"}}',
            '{"type":"final_answer","answer":"문서 전체 내용에는 간이지급명세서와 총지급액 120000원이 포함되어 있습니다."}',
        ]
    )
    container = build_container(
        settings=_settings_without_env(upload_dir=str(upload_dir)),
        llm_gateway=llm_gateway,
        pdf_parser=_fake_pdf_parser,
    )
    app = create_app(settings=container.settings, container=container)
    with TestClient(app) as client:
        upload_response = client.post(
            "/uploads",
            content=b"%PDF-1.7 fake",
            headers={
                "Content-Type": "application/pdf",
                "X-Filename": "invoice.pdf",
                "X-Session-Id": "session-doc-question",
            },
        )
        chat_response = client.post(
            "/chat",
            json={"message": "전체 내용을 설명해 줘", "session_id": "session-doc-question"},
        )

    assert upload_response.status_code == 200
    assert chat_response.status_code == 200
    assert (
        chat_response.json()["message"]
        == "문서 전체 내용에는 간이지급명세서와 총지급액 120000원이 포함되어 있습니다."
    )
    assert len(llm_gateway.chatted_messages) == 4


def test_chat_route_falls_back_when_document_agent_returns_invalid_json(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    llm_gateway = StubDocumentLlmGateway(chat_response="not-json")
    container = build_container(
        settings=_settings_without_env(upload_dir=str(upload_dir)),
        llm_gateway=llm_gateway,
        pdf_parser=_fake_pdf_parser,
    )
    app = create_app(settings=container.settings, container=container)

    with TestClient(app) as client:
        upload_response = client.post(
            "/uploads",
            content=b"%PDF-1.7 fake",
            headers={
                "Content-Type": "application/pdf",
                "X-Filename": "invoice.pdf",
                "X-Session-Id": "session-fallback",
            },
        )
        chat_response = client.post(
            "/chat",
            json={"message": "해당 문서를 읽고 분석해 줘", "session_id": "session-fallback"},
        )

    assert upload_response.status_code == 200
    assert chat_response.status_code == 200
    assert "문서 분석을 완료했습니다." in chat_response.json()["message"]
    assert "총지급액: 120000원" in chat_response.json()["message"]
