from pathlib import Path

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.workflow.document_workflow import (
    create_document_workflow,
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement
from docflow_agent.workflow.document_services import bind_document_workflow_services


def test_prompt_routes_to_document_process_and_creates_artifact_refs() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=bind_document_workflow_services(artifact_repository=repository),
        artifact_repository=repository,
    )

    state = workflow.invoke({"user_input": "엑셀 문서를 분석해줘"})

    assert state["flow"] == "document_process"
    assert state["source_refs"]
    assert state["unit_refs"]
    assert state["bundle_refs"]
    assert state["output_refs"]
    assert state["output_refs"][-1]["kind"] == "analysis"
    assert state["result"]


def test_workflow_facade_accepts_human_decisions_and_serializes_state() -> None:
    repository = InMemoryArtifactRepository()
    workflow = create_document_workflow(
        usecases=bind_document_workflow_services(artifact_repository=repository),
        artifact_repository=repository,
    )

    state = invoke_document_workflow(
        user_input="엑셀에서 미정산 건을 찾아 메일로 보내줘",
        human_decisions=[
            {
                "decision_id": "approve_send_mail",
                "kind": "approve",
                "message": "Approve sending the generated mail draft?",
                "options": ["approve", "reject"],
                "selected": "approve",
                "payload": None,
            }
        ],
        workflow=workflow,
    )

    response = workflow_state_to_response(state)

    assert response["flow"] == "document_to_mail"
    assert response["current_step"] == "send_mail"
    assert response["result"] == "Mail sent after approval."
    assert response["output_refs"]


def test_prompt_with_pdf_path_routes_through_pdf_parsing(tmp_path: Path) -> None:
    repository = InMemoryArtifactRepository()
    pdf_path = tmp_path / "statement.pdf"
    pdf_path.write_bytes(b"%PDF-1.7 fake")

    def fake_pdf_parser(client: OpenDataLoaderPdfClient, file_info: FileInfo) -> PdfDocument:
        assert client.use_struct_tree is True
        assert file_info.path == str(pdf_path)
        return PdfDocument(
            file_name="statement.pdf",
            page_count=1,
            markdown="# Statement",
            elements=[
                PdfElement(
                    element_type="heading",
                    page_number=1,
                    content="Statement",
                    bounding_box=[72.0, 700.0, 540.0, 730.0],
                )
            ],
        )

    workflow = create_document_workflow(
        usecases=bind_document_workflow_services(
            artifact_repository=repository,
            pdf_client=OpenDataLoaderPdfClient(),
            pdf_parser=fake_pdf_parser,
        ),
        artifact_repository=repository,
    )

    state = workflow.invoke({"user_input": f"이 PDF 파일을 분석해줘 {pdf_path}"})

    assert state["flow"] == "document_process"
    assert state["unit_refs"]
    first_unit = repository.load("unit", state["unit_refs"][0]["ref_id"])
    assert first_unit["name"] == "pdf_page_1"
    assert first_unit["content"] == "Statement"
