from pathlib import Path

from langgraph.store.memory import InMemoryStore

from docflow_agent.config.prompt import get_document_agent_system_prompt
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.session_context import StoreBackedSessionDocumentStore
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement
from docflow_agent.usecases.document_workflow import bind_document_usecases
from docflow_agent.workflow.document_agent import DocumentAgentRuntime
from docflow_agent.workflow.tools import (
    bind_document_agent_tools,
    DocumentAgentToolContext,
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


def _build_runtime(tmp_path: Path, llm_gateway: StubDocumentLlmGateway) -> DocumentAgentRuntime:
    repository = InMemoryArtifactRepository()
    runtime_store = InMemoryStore()
    session_document_store = StoreBackedSessionDocumentStore(store=runtime_store)
    usecases = bind_document_usecases(
        artifact_repository=repository,
        llm_gateway=llm_gateway,
        pdf_client=OpenDataLoaderPdfClient(),
        pdf_parser=_fake_pdf_parser,
    )
    source_path = tmp_path / "statement.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")
    source_ref_id = usecases["register_uploaded_source"](
        FileInfo(
            name="statement.pdf",
            path=str(source_path),
            content_type="application/pdf",
        )
    )
    session_document_store.set_current_source_ref("session-001", source_ref_id)
    return DocumentAgentRuntime(
        llm_gateway=llm_gateway,
        tools=bind_document_agent_tools(
            build_document_payload=usecases["build_document_payload"],
            summarize_source_ref=usecases["summarize_source_ref"],
        ),
        tool_context=DocumentAgentToolContext(
            session_id="session-001",
        ),
        runtime_store=runtime_store,
        system_prompt=get_document_agent_system_prompt(),
    )


def test_document_agent_runtime_runs_summary_trajectory(tmp_path: Path) -> None:
    llm_gateway = StubDocumentLlmGateway(
        chat_responses=[
            '{"type":"tool_call","tool":"get_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"parse_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"summarize_current_document","arguments":{}}',
            '{"type":"final_answer","answer":"문서 분석 결과: 간이지급명세서와 총지급액 120000원입니다."}',
        ]
    )
    runtime = _build_runtime(tmp_path, llm_gateway)

    result = runtime.run(prompt="해당 문서를 분석해 줘")

    assert result.answer == "문서 분석 결과: 간이지급명세서와 총지급액 120000원입니다."
    assert [call.tool_name for call in result.trace.tool_calls] == [
        "get_current_document",
        "parse_current_document",
        "summarize_current_document",
    ]


def test_document_agent_runtime_runs_question_trajectory(tmp_path: Path) -> None:
    llm_gateway = StubDocumentLlmGateway(
        chat_responses=[
            '{"type":"tool_call","tool":"get_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"parse_current_document","arguments":{}}',
            '{"type":"tool_call","tool":"answer_about_current_document","arguments":{"question":"이 문서의 금액은 뭐야?"}}',
            '{"type":"final_answer","answer":"이 문서의 총지급액은 120000원입니다."}',
        ]
    )
    runtime = _build_runtime(tmp_path, llm_gateway)

    result = runtime.run(prompt="이 문서의 금액은 뭐야?")

    assert result.answer == "이 문서의 총지급액은 120000원입니다."
    assert [call.tool_name for call in result.trace.tool_calls] == [
        "get_current_document",
        "parse_current_document",
        "answer_about_current_document",
    ]
    assert '"question": "이 문서의 금액은 뭐야?"' in result.trace.tool_calls[-1].tool_input_summary
