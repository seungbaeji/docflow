import os
from pathlib import Path

import pytest

from docflow_agent.bootstrap import build_container
from docflow_agent.config.prompt import get_document_agent_system_prompt
from docflow_agent.config.settings import get_settings
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement
from docflow_agent.types.value.document_agent import DocumentAgentToolContext
from docflow_agent.workflow.document_agent import DocumentAgentRuntime
from docflow_agent.tools import DOCUMENT_AGENT_TOOLS
from docflow_agent.testing.document_workflow import build_document_workflow_functions


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
    usecases = build_document_workflow_functions(
        artifact_repository=container.artifact_repository,
        llm_gateway=container.llm_gateway,
        workflow_run_store=container.workflow_run_store,
        vector_store=container.vector_store,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )
    source_path = tmp_path / "statement.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")
    upload_id = usecases["stage_upload"](
        "statement.pdf",
        str(source_path),
        "application/pdf",
        len(b"%PDF-1.7 fake"),
    )
    source_ref_id = usecases["source_from_upload"](upload_id)
    container.session_document_store.set_current_source_ref("smoke-session", source_ref_id)
    document_payload = usecases["build_payload"](source_ref_id)
    document_summary = usecases["summarize_ref"](source_ref_id)

    runtime = DocumentAgentRuntime(
        llm_gateway=container.llm_gateway,
        tools=DOCUMENT_AGENT_TOOLS,
        tool_context=DocumentAgentToolContext(
            source_ref_id=source_ref_id,
            document_payload=document_payload,
            document_summary=document_summary,
        ),
        runtime_store=container.runtime_store,
        system_prompt=get_document_agent_system_prompt(),
    )

    result = runtime.run(prompt="해당 문서를 분석해 줘")

    assert result.answer.strip()
    assert result.trace.tool_calls
