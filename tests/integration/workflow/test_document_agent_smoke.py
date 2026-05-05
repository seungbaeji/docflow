import os
from pathlib import Path

import pytest

from docflow_agent.bootstrap import build_container
from docflow_agent.config.prompt import get_document_agent_system_prompt
from docflow_agent.config.settings import get_settings
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases
from docflow_agent.workflow.document_agent import DocumentAgentRuntime
from docflow_agent.workflow.tools import build_document_agent_tools


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


@pytest.mark.real_provider
def test_document_agent_smoke_with_real_provider(tmp_path: Path) -> None:
    if os.environ.get("DOCFLOW_AGENT_REAL_PROVIDER_SMOKE") != "1":
        pytest.skip("Set DOCFLOW_AGENT_REAL_PROVIDER_SMOKE=1 to run real-provider smoke tests.")

    settings = get_settings()
    if settings.llm.provider == "stub":
        pytest.skip("Configure a real llm provider before running the smoke test.")

    container = build_container(settings=settings, pdf_parser=_fake_pdf_parser)
    usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=container.artifact_repository,
        llm_gateway=container.llm_gateway,
        workflow_run_store=container.workflow_run_store,
        vector_store=container.vector_store,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )
    source_path = tmp_path / "statement.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")
    source_ref_id = usecases.register_uploaded_source(
        FileInfo(
            name="statement.pdf",
            path=str(source_path),
            content_type="application/pdf",
        )
    )
    container.session_document_store.set_current_source_ref("smoke-session", source_ref_id)

    runtime = DocumentAgentRuntime(
        llm_gateway=container.llm_gateway,
        tools=build_document_agent_tools(
            session_document_store=container.session_document_store,
            document_usecases=usecases,
        ),
        system_prompt=get_document_agent_system_prompt(),
    )

    result = runtime.run(prompt="해당 문서를 분석해 줘", session_id="smoke-session")

    assert result.answer.strip()
    assert result.trace.tool_calls
