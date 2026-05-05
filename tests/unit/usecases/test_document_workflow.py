from pathlib import Path

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.rdbms import InMemoryWorkflowRunStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement
from docflow_agent.testing.document_workflow import build_document_workflow_functions


def test_analyze_persists_record_and_vector_document() -> None:
    repository = InMemoryArtifactRepository()
    workflow_run_store = InMemoryWorkflowRunStore()
    vector_store = InMemoryVectorStore()
    usecases = build_document_workflow_functions(
        artifact_repository=repository,
        workflow_run_store=workflow_run_store,
        vector_store=vector_store,
    )

    bundle_ref_id = repository.save(
        "bundle",
        {
            "category": "invoice",
            "unit_ref_ids": ["unit-001", "unit-002"],
            "source_ref_id": "source-001",
        },
        metadata={"stage": "combined"},
    )

    outcome = usecases["analyze"](bundle_ref_id)

    record = workflow_run_store.load_workflow_run(outcome.ref_id)
    assert record.status == "analyzed"
    assert record.artifact_refs == [bundle_ref_id, outcome.ref_id]
    hits = vector_store.search_similar("analysis invoice", limit=1)
    assert hits
    assert hits[0].document_id == outcome.ref_id


def test_compose_mail_uses_llm_gateway_when_available() -> None:
    repository = InMemoryArtifactRepository()
    llm_gateway = StubDocumentLlmGateway(summary_response="LLM generated mail body")
    usecases = build_document_workflow_functions(
        artifact_repository=repository,
        llm_gateway=llm_gateway,
    )

    dataset_ref_id = repository.save(
        "dataset",
        {
            "bundle_ref_id": "bundle-001",
            "records": [{"status": "unsettled", "recipient": "ops@example.com"}],
        },
        metadata={"stage": "filtered"},
    )

    draft_ref_id = usecases["compose_mail"](dataset_ref_id)

    draft = repository.load("draft", draft_ref_id)
    assert draft["body"] == "LLM generated mail body"
    assert llm_gateway.summarized_payloads


def test_send_mail_persists_record() -> None:
    repository = InMemoryArtifactRepository()
    workflow_run_store = InMemoryWorkflowRunStore()
    usecases = build_document_workflow_functions(
        artifact_repository=repository,
        workflow_run_store=workflow_run_store,
    )

    draft_ref_id = repository.save(
        "draft",
        {"dataset_ref_id": "dataset-001", "to": ["ops@example.com"]},
        metadata={"stage": "composed"},
    )

    outcome = usecases["send_mail"](draft_ref_id)

    record = workflow_run_store.load_workflow_run(outcome.ref_id)
    assert record.status == "sent"


def test_parse_units_uses_pdf_adapter_for_pdf_source(tmp_path: Path) -> None:
    repository = InMemoryArtifactRepository()
    source_path = tmp_path / "invoice.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")

    def fake_pdf_parser(client: OpenDataLoaderPdfClient, file_info: FileInfo) -> PdfDocument:
        assert client.format == "markdown,json"
        assert file_info.path == str(source_path)
        return PdfDocument(
            file_name="invoice.pdf",
            page_count=2,
            markdown="# Invoice\nAmount due",
            elements=[
                PdfElement(
                    element_type="heading",
                    page_number=1,
                    content="Invoice",
                    bounding_box=[72.0, 700.0, 540.0, 730.0],
                ),
                PdfElement(
                    element_type="paragraph",
                    page_number=2,
                    content="Amount due",
                    bounding_box=[72.0, 640.0, 540.0, 680.0],
                ),
            ],
        )

    usecases = build_document_workflow_functions(
        artifact_repository=repository,
        pdf_client=OpenDataLoaderPdfClient(),
        pdf_parser=fake_pdf_parser,
    )

    source_ref_id = usecases["load_source"](f"이 PDF 파일을 분석해줘 {source_path}")
    unit_ref_ids = usecases["parse_units"](source_ref_id)

    assert len(unit_ref_ids) == 2
    first_unit = repository.load("unit", unit_ref_ids[0])
    second_unit = repository.load("unit", unit_ref_ids[1])
    assert first_unit["name"] == "pdf_page_1"
    assert second_unit["name"] == "pdf_page_2"
    assert first_unit["content"] == "Invoice"
    assert second_unit["content"] == "Amount due"

    parsed_refs = repository.find("analysis", {"stage": "pdf_parsed"})
    assert parsed_refs
    parsed_document = repository.load("analysis", parsed_refs[0])
    assert parsed_document["file_name"] == "invoice.pdf"


def test_summarize_ref_returns_human_readable_summary(tmp_path: Path) -> None:
    repository = InMemoryArtifactRepository()
    source_path = tmp_path / "statement.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")

    def fake_pdf_parser(client: OpenDataLoaderPdfClient, file_info: FileInfo) -> PdfDocument:
        assert client.format == "markdown,json"
        assert file_info.path == str(source_path)
        return PdfDocument(
            file_name="statement.pdf",
            page_count=1,
            markdown="# Payment statement\nTotal amount: 120000 KRW",
            elements=[
                PdfElement(
                    element_type="paragraph",
                    page_number=1,
                    content="Total amount: 120000 KRW",
                    bounding_box=[72.0, 640.0, 540.0, 680.0],
                ),
            ],
        )

    usecases = build_document_workflow_functions(
        artifact_repository=repository,
        pdf_client=OpenDataLoaderPdfClient(),
        pdf_parser=fake_pdf_parser,
    )

    source_ref_id = usecases["load_source"](f"이 PDF 파일을 분석해줘 {source_path}")
    summary = usecases["summarize_ref"](source_ref_id)

    assert "문서 분석을 완료했습니다." in summary
    assert "- 문서 유형: pdf" in summary
    assert "- 파일명: statement.pdf" in summary
    assert "- 감지된 페이지 수: 1" in summary
    assert "Total amount: 120000 KRW" in summary


def test_answer_question_about_ref_uses_full_payload(tmp_path: Path) -> None:
    repository = InMemoryArtifactRepository()
    llm_gateway = StubDocumentLlmGateway(answer_response="질문 응답")
    source_path = tmp_path / "statement.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")

    def fake_pdf_parser(client: OpenDataLoaderPdfClient, file_info: FileInfo) -> PdfDocument:
        assert client.format == "markdown,json"
        assert file_info.path == str(source_path)
        return PdfDocument(
            file_name="statement.pdf",
            page_count=1,
            markdown="# Payment statement\nTotal amount: 120000 KRW",
            text="Payment statement\nTotal amount: 120000 KRW",
            elements=[
                PdfElement(
                    element_type="paragraph",
                    page_number=1,
                    content="Total amount: 120000 KRW",
                    bounding_box=[72.0, 640.0, 540.0, 680.0],
                ),
            ],
        )

    usecases = build_document_workflow_functions(
        artifact_repository=repository,
        llm_gateway=llm_gateway,
        pdf_client=OpenDataLoaderPdfClient(),
        pdf_parser=fake_pdf_parser,
    )

    source_ref_id = usecases["load_source"](f"이 PDF 파일을 분석해줘 {source_path}")
    answer = usecases["answer_question_about_ref"](source_ref_id, "전체 내용을 설명해 줘")

    assert answer == "질문 응답"
    assert llm_gateway.asked_questions
    asked_question, payload = llm_gateway.asked_questions[0]
    assert asked_question == "전체 내용을 설명해 줘"
    assert payload["file_name"] == "statement.pdf"
    assert payload["page_count"] == 1
    assert payload["markdown"] == "# Payment statement\nTotal amount: 120000 KRW"
    assert payload["text"] == "Payment statement\nTotal amount: 120000 KRW"
