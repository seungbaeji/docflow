from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import TypedDict

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient, extract_pdf_document
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, VectorStoreDocument, WorkflowRunRecord
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.types.value.results import UsecaseOutcome

PdfParser = Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument]


class DocumentUsecaseBindings(TypedDict):
    load_source: Callable[[str], str]
    register_uploaded_source: Callable[[FileInfo], str]
    parse_units: Callable[[str], list[str]]
    process_source_ref: Callable[[str], UsecaseOutcome]
    summarize_source_ref: Callable[[str], str]
    answer_question_about_source_ref: Callable[[str, str], str]
    build_document_context: Callable[[str], str]
    categorize_units: Callable[[list[str]], list[str]]
    combine_bundle: Callable[[list[str]], str]
    analyze: Callable[[str], UsecaseOutcome]
    filter_dataset: Callable[[str], str]
    compose_mail: Callable[[str], str]
    send_mail: Callable[[str], UsecaseOutcome]
    reject_send_mail: Callable[[str | None], UsecaseOutcome]
    handle_unknown: Callable[[str], UsecaseOutcome]
    build_document_payload: Callable[[str], DocumentPayload]


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


def _extract_pdf_path(user_input: str) -> str | None:
    for token in user_input.replace('"', " ").replace("'", " ").split():
        candidate = Path(token.strip())
        if candidate.suffix.casefold() == ".pdf":
            return str(candidate)
    return None


def load_source(
    user_input: str,
    *,
    artifact_repository: ArtifactRepository,
) -> str:
    pdf_path = _extract_pdf_path(user_input)
    source_payload = {
        "prompt": user_input,
        "source_type": (
            "pdf"
            if pdf_path is not None
            else "excel"
            if _contains_any(user_input, ("excel", "엑셀", "document", "문서"))
            else "generic"
        ),
        "file_path": pdf_path,
    }
    return artifact_repository.save(
        kind="source",
        value=source_payload,
        metadata={"stage": "loaded"},
    )


def register_uploaded_source(
    file_info: FileInfo,
    *,
    artifact_repository: ArtifactRepository,
) -> str:
    source_type = "pdf" if file_info.content_type == "application/pdf" else "generic"
    return artifact_repository.save(
        kind="source",
        value={
            "prompt": f"Uploaded file {file_info.name}",
            "source_type": source_type,
            "file_path": file_info.path,
            "file_name": file_info.name,
            "content_type": file_info.content_type,
            "uploaded": True,
        },
        metadata={"stage": "uploaded"},
    )


def parse_units(
    source_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> list[str]:
    source = artifact_repository.load("source", source_ref_id)
    prompt = str(source["prompt"])
    if source.get("source_type") == "pdf":
        return _parse_pdf_units(
            source_ref_id=source_ref_id,
            source=source,
            artifact_repository=artifact_repository,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    unit_names = (
        ["settlement_sheet", "mail_targets"]
        if _contains_any(prompt, ("mail", "메일", "send", "보내", "미정산"))
        else ["document_main", "document_summary"]
    )
    unit_refs: list[str] = []
    for unit_name in unit_names:
        ref_id = artifact_repository.save(
            kind="unit",
            value={"name": unit_name, "source_ref_id": source_ref_id, "prompt": prompt},
            metadata={"source_ref_id": source_ref_id, "stage": "parsed"},
        )
        unit_refs.append(ref_id)
    return unit_refs


def process_source_ref(
    source_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> UsecaseOutcome:
    parsed_unit_ref_ids = _get_existing_unit_refs(
        artifact_repository=artifact_repository,
        source_ref_id=source_ref_id,
        stage="parsed",
    )
    if not parsed_unit_ref_ids:
        parsed_unit_ref_ids = parse_units(
            source_ref_id,
            artifact_repository=artifact_repository,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    categorized_unit_ref_ids = categorize_units(
        parsed_unit_ref_ids,
        artifact_repository=artifact_repository,
    )
    bundle_ref_id = combine_bundle(
        categorized_unit_ref_ids,
        artifact_repository=artifact_repository,
    )
    return analyze(
        bundle_ref_id,
        artifact_repository=artifact_repository,
        workflow_run_store=workflow_run_store,
        vector_store=vector_store,
    )


def summarize_source_ref(
    source_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> str:
    del llm_gateway
    outcome = process_source_ref(
        source_ref_id,
        artifact_repository=artifact_repository,
        workflow_run_store=workflow_run_store,
        vector_store=vector_store,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    payload = build_document_payload(
        source_ref_id,
        artifact_repository=artifact_repository,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
        analysis_ref_id=outcome.ref_id,
    )
    return _render_document_summary(payload)


def answer_question_about_source_ref(
    source_ref_id: str,
    question: str,
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> str:
    if llm_gateway is None:
        return summarize_source_ref(
            source_ref_id,
            artifact_repository=artifact_repository,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )
    payload = build_document_payload(
        source_ref_id,
        artifact_repository=artifact_repository,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    return llm_gateway.ask_document_question(question=question, payload=asdict(payload))


def build_document_context(
    source_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> str:
    payload = build_document_payload(
        source_ref_id,
        artifact_repository=artifact_repository,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    return "\n".join(
        [
            f"source_type={payload.source_type}",
            f"file_name={payload.file_name}",
            f"file_path={payload.file_path}",
            f"page_count={payload.page_count}",
            f"unit_count={payload.unit_count}",
            "unit_summaries:",
            *[f"- {summary}" for summary in payload.unit_summaries],
        ]
    )


def categorize_units(
    unit_ref_ids: list[str],
    *,
    artifact_repository: ArtifactRepository,
) -> list[str]:
    categorized_refs: list[str] = []
    for unit_ref_id in unit_ref_ids:
        unit = artifact_repository.load("unit", unit_ref_id)
        categorized_ref_id = artifact_repository.save(
            kind="unit",
            value={
                **unit,
                "category": "invoice"
                if _contains_any(str(unit["prompt"]), ("excel", "엑셀", "정산", "invoice"))
                else "general",
            },
            metadata={"parent_unit_ref_id": unit_ref_id, "stage": "categorized"},
        )
        categorized_refs.append(categorized_ref_id)
    return categorized_refs


def combine_bundle(
    unit_ref_ids: list[str],
    *,
    artifact_repository: ArtifactRepository,
) -> str:
    units = [artifact_repository.load("unit", unit_ref_id) for unit_ref_id in unit_ref_ids]
    bundle = {
        "category": units[0].get("category", "general") if units else "general",
        "unit_ref_ids": unit_ref_ids,
        "source_ref_id": units[0]["source_ref_id"] if units else None,
    }
    return artifact_repository.save(
        kind="bundle",
        value=bundle,
        metadata={"stage": "combined"},
    )


def analyze(
    bundle_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
) -> UsecaseOutcome:
    bundle = artifact_repository.load("bundle", bundle_ref_id)
    analysis_ref_id = artifact_repository.save(
        kind="analysis",
        value={
            "bundle_ref_id": bundle_ref_id,
            "unit_count": len(bundle["unit_ref_ids"]),
            "category": bundle["category"],
        },
        metadata={"bundle_ref_id": bundle_ref_id, "stage": "analyzed"},
    )
    _save_workflow_run(
        workflow_run_store=workflow_run_store,
        record_id=analysis_ref_id,
        status="analyzed",
        artifact_refs=[bundle_ref_id, analysis_ref_id],
        metadata={"bundle_ref_id": bundle_ref_id, "category": str(bundle["category"])},
    )
    _upsert_vector_document(
        vector_store=vector_store,
        document_id=analysis_ref_id,
        text=f"Analysis for {bundle_ref_id} category={bundle['category']}",
        metadata={"bundle_ref_id": bundle_ref_id, "kind": "analysis"},
    )
    return UsecaseOutcome(
        ref_id=analysis_ref_id,
        message=f"Document processed with {len(bundle['unit_ref_ids'])} categorized units.",
    )


def filter_dataset(
    bundle_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
) -> str:
    return artifact_repository.save(
        kind="dataset",
        value={
            "bundle_ref_id": bundle_ref_id,
            "records": [{"status": "unsettled", "recipient": "ops@example.com"}],
        },
        metadata={"bundle_ref_id": bundle_ref_id, "stage": "filtered"},
    )


def compose_mail(
    dataset_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
) -> str:
    dataset = artifact_repository.load("dataset", dataset_ref_id)
    body = "Please review the unsettled items from the document workflow."
    if llm_gateway is not None:
        body = llm_gateway.summarize_document(
            {
                "dataset_ref_id": dataset_ref_id,
                "records": dataset["records"],
                "task": "Compose an internal mail summary for unsettled items.",
            }
        )
    return artifact_repository.save(
        kind="draft",
        value={
            "dataset_ref_id": dataset_ref_id,
            "to": ["ops@example.com"],
            "subject": "Unsettled items report",
            "body": body,
        },
        metadata={"dataset_ref_id": dataset_ref_id, "stage": "composed"},
    )


def send_mail(
    draft_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    workflow_run_store: WorkflowRunStore | None = None,
) -> UsecaseOutcome:
    result_ref_id = artifact_repository.save(
        kind="result",
        value={"draft_ref_id": draft_ref_id, "status": "sent"},
        metadata={"draft_ref_id": draft_ref_id, "stage": "sent"},
    )
    _save_workflow_run(
        workflow_run_store=workflow_run_store,
        record_id=result_ref_id,
        status="sent",
        artifact_refs=[draft_ref_id, result_ref_id],
        metadata={"draft_ref_id": draft_ref_id},
    )
    return UsecaseOutcome(ref_id=result_ref_id, message="Mail sent after approval.")


def reject_send_mail(
    draft_ref_id: str | None,
    *,
    artifact_repository: ArtifactRepository,
    workflow_run_store: WorkflowRunStore | None = None,
) -> UsecaseOutcome:
    result_ref_id = artifact_repository.save(
        kind="result",
        value={"draft_ref_id": draft_ref_id, "status": "rejected"},
        metadata={"draft_ref_id": draft_ref_id, "stage": "rejected"},
    )
    _save_workflow_run(
        workflow_run_store=workflow_run_store,
        record_id=result_ref_id,
        status="rejected",
        artifact_refs=[ref for ref in [draft_ref_id, result_ref_id] if ref is not None],
        metadata={"draft_ref_id": draft_ref_id},
    )
    return UsecaseOutcome(ref_id=result_ref_id, message="User rejected mail sending.")


def handle_unknown(
    user_input: str,
    *,
    artifact_repository: ArtifactRepository,
    workflow_run_store: WorkflowRunStore | None = None,
) -> UsecaseOutcome:
    result_ref_id = artifact_repository.save(
        kind="result",
        value={"prompt": user_input, "status": "unknown"},
        metadata={"stage": "unknown"},
    )
    _save_workflow_run(
        workflow_run_store=workflow_run_store,
        record_id=result_ref_id,
        status="unknown",
        artifact_refs=[result_ref_id],
        metadata={"prompt": user_input},
    )
    return UsecaseOutcome(
        ref_id=result_ref_id,
        message="Unable to determine a supported workflow for the request.",
    )


def build_document_payload(
    source_ref_id: str,
    *,
    artifact_repository: ArtifactRepository,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
    analysis_ref_id: str | None = None,
) -> DocumentPayload:
    source = artifact_repository.load("source", source_ref_id)
    parsed_unit_ref_ids = _get_existing_unit_refs(
        artifact_repository=artifact_repository,
        source_ref_id=source_ref_id,
        stage="parsed",
    )
    if not parsed_unit_ref_ids:
        parsed_unit_ref_ids = parse_units(
            source_ref_id,
            artifact_repository=artifact_repository,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    unit_summaries: list[str] = []
    for unit_ref_id in parsed_unit_ref_ids[:3]:
        unit = artifact_repository.load("unit", unit_ref_id)
        content = unit.get("content")
        if isinstance(content, str) and content.strip():
            summary = content.strip()
        else:
            summary = str(unit.get("name", "document_unit"))
        unit_summaries.append(summary[:400])

    pdf_parsed_ref_ids = artifact_repository.find(
        "analysis",
        {"source_ref_id": source_ref_id, "stage": "pdf_parsed"},
    )
    parsed_document = (
        artifact_repository.load("analysis", pdf_parsed_ref_ids[-1])
        if pdf_parsed_ref_ids
        else None
    )
    analysis = (
        artifact_repository.load("analysis", analysis_ref_id)
        if analysis_ref_id is not None
        else None
    )

    page_count = 0
    markdown = None
    text = None
    markdown_excerpt = None
    if isinstance(parsed_document, dict):
        raw_page_count = parsed_document.get("page_count")
        if isinstance(raw_page_count, int):
            page_count = raw_page_count
        raw_markdown = parsed_document.get("markdown")
        if isinstance(raw_markdown, str):
            markdown = raw_markdown
            if raw_markdown.strip():
                markdown_excerpt = raw_markdown.strip()[:800]
        raw_text = parsed_document.get("text")
        if isinstance(raw_text, str):
            text = raw_text

    return DocumentPayload(
        source_ref_id=source_ref_id,
        source_type=str(source.get("source_type", "unknown")),
        file_name=str(source.get("file_name") or Path(str(source.get("file_path") or "")).name),
        file_path=str(source.get("file_path") or ""),
        page_count=page_count,
        unit_count=len(parsed_unit_ref_ids),
        unit_summaries=unit_summaries,
        parsed_unit_ref_ids=parsed_unit_ref_ids,
        markdown=markdown,
        text=text,
        markdown_excerpt=markdown_excerpt,
        analysis=analysis if isinstance(analysis, dict) else None,
    )


def bind_document_usecases(
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> DocumentUsecaseBindings:
    def bound_load_source(user_input: str) -> str:
        return load_source(user_input, artifact_repository=artifact_repository)

    def bound_register_uploaded_source(file_info: FileInfo) -> str:
        return register_uploaded_source(file_info, artifact_repository=artifact_repository)

    def bound_parse_units(source_ref_id: str) -> list[str]:
        return parse_units(
            source_ref_id,
            artifact_repository=artifact_repository,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    def bound_process_source_ref(source_ref_id: str) -> UsecaseOutcome:
        return process_source_ref(
            source_ref_id,
            artifact_repository=artifact_repository,
            llm_gateway=llm_gateway,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    def bound_summarize_source_ref(source_ref_id: str) -> str:
        return summarize_source_ref(
            source_ref_id,
            artifact_repository=artifact_repository,
            llm_gateway=llm_gateway,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    def bound_answer_question_about_source_ref(source_ref_id: str, question: str) -> str:
        return answer_question_about_source_ref(
            source_ref_id,
            question,
            artifact_repository=artifact_repository,
            llm_gateway=llm_gateway,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    def bound_build_document_context(source_ref_id: str) -> str:
        return build_document_context(
            source_ref_id,
            artifact_repository=artifact_repository,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    def bound_categorize_units(unit_ref_ids: list[str]) -> list[str]:
        return categorize_units(unit_ref_ids, artifact_repository=artifact_repository)

    def bound_combine_bundle(unit_ref_ids: list[str]) -> str:
        return combine_bundle(unit_ref_ids, artifact_repository=artifact_repository)

    def bound_analyze(bundle_ref_id: str) -> UsecaseOutcome:
        return analyze(
            bundle_ref_id,
            artifact_repository=artifact_repository,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
        )

    def bound_filter_dataset(bundle_ref_id: str) -> str:
        return filter_dataset(bundle_ref_id, artifact_repository=artifact_repository)

    def bound_compose_mail(dataset_ref_id: str) -> str:
        return compose_mail(
            dataset_ref_id,
            artifact_repository=artifact_repository,
            llm_gateway=llm_gateway,
        )

    def bound_send_mail(draft_ref_id: str) -> UsecaseOutcome:
        return send_mail(
            draft_ref_id,
            artifact_repository=artifact_repository,
            workflow_run_store=workflow_run_store,
        )

    def bound_reject_send_mail(draft_ref_id: str | None) -> UsecaseOutcome:
        return reject_send_mail(
            draft_ref_id,
            artifact_repository=artifact_repository,
            workflow_run_store=workflow_run_store,
        )

    def bound_handle_unknown(user_input: str) -> UsecaseOutcome:
        return handle_unknown(
            user_input,
            artifact_repository=artifact_repository,
            workflow_run_store=workflow_run_store,
        )

    def bound_build_document_payload(source_ref_id: str) -> DocumentPayload:
        return build_document_payload(
            source_ref_id,
            artifact_repository=artifact_repository,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )

    return {
        "load_source": bound_load_source,
        "register_uploaded_source": bound_register_uploaded_source,
        "parse_units": bound_parse_units,
        "process_source_ref": bound_process_source_ref,
        "summarize_source_ref": bound_summarize_source_ref,
        "answer_question_about_source_ref": bound_answer_question_about_source_ref,
        "build_document_context": bound_build_document_context,
        "categorize_units": bound_categorize_units,
        "combine_bundle": bound_combine_bundle,
        "analyze": bound_analyze,
        "filter_dataset": bound_filter_dataset,
        "compose_mail": bound_compose_mail,
        "send_mail": bound_send_mail,
        "reject_send_mail": bound_reject_send_mail,
        "handle_unknown": bound_handle_unknown,
        "build_document_payload": bound_build_document_payload,
    }


def _parse_pdf_units(
    *,
    source_ref_id: str,
    source: dict[str, object],
    artifact_repository: ArtifactRepository,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: PdfParser,
) -> list[str]:
    file_path = source.get("file_path")
    if not isinstance(file_path, str) or pdf_client is None:
        return _save_generic_pdf_units(
            source_ref_id=source_ref_id,
            source=source,
            artifact_repository=artifact_repository,
        )

    file_info = FileInfo(
        name=Path(file_path).name,
        path=file_path,
        content_type="application/pdf",
    )
    parsed_document = pdf_parser(pdf_client, file_info)
    parsed_ref_id = artifact_repository.save(
        kind="analysis",
        value=parsed_document.model_dump(mode="python"),
        metadata={"source_ref_id": source_ref_id, "stage": "pdf_parsed"},
    )

    page_numbers = sorted(
        {
            element.page_number
            for element in parsed_document.elements
            if element.page_number is not None
        }
    )
    if not page_numbers:
        return _save_generic_pdf_units(
            source_ref_id=source_ref_id,
            source=source,
            artifact_repository=artifact_repository,
            parsed_ref_id=parsed_ref_id,
            markdown=parsed_document.markdown,
        )

    unit_refs: list[str] = []
    for page_number in page_numbers:
        page_elements = [
            element for element in parsed_document.elements if element.page_number == page_number
        ]
        page_content = "\n".join(
            element.content for element in page_elements if element.content is not None
        )
        ref_id = artifact_repository.save(
            kind="unit",
            value={
                "name": f"pdf_page_{page_number}",
                "source_ref_id": source_ref_id,
                "prompt": str(source["prompt"]),
                "page_number": page_number,
                "content": page_content,
                "element_count": len(page_elements),
                "parsed_ref_id": parsed_ref_id,
            },
            metadata={
                "source_ref_id": source_ref_id,
                "stage": "parsed",
                "page_number": page_number,
                "parsed_ref_id": parsed_ref_id,
            },
        )
        unit_refs.append(ref_id)
    return unit_refs


def _save_generic_pdf_units(
    *,
    source_ref_id: str,
    source: dict[str, object],
    artifact_repository: ArtifactRepository,
    parsed_ref_id: str | None = None,
    markdown: str | None = None,
) -> list[str]:
    ref_id = artifact_repository.save(
        kind="unit",
        value={
            "name": "pdf_document",
            "source_ref_id": source_ref_id,
            "prompt": str(source["prompt"]),
            "content": markdown,
            "parsed_ref_id": parsed_ref_id,
        },
        metadata={
            "source_ref_id": source_ref_id,
            "stage": "parsed",
            "parsed_ref_id": parsed_ref_id,
        },
    )
    return [ref_id]


def _save_workflow_run(
    *,
    workflow_run_store: WorkflowRunStore | None,
    record_id: str,
    status: str,
    artifact_refs: list[str],
    metadata: dict[str, object],
) -> None:
    if workflow_run_store is None:
        return
    workflow_run_store.save_workflow_run(
        WorkflowRunRecord(
            record_id=record_id,
            status=status,
            artifact_refs=artifact_refs,
            metadata=metadata,
        )
    )


def _upsert_vector_document(
    *,
    vector_store: VectorStorePort | None,
    document_id: str,
    text: str,
    metadata: dict[str, object],
) -> None:
    if vector_store is None:
        return
    vector_store.upsert_documents(
        [
            VectorStoreDocument(
                document_id=document_id,
                text=text,
                metadata=metadata,
            )
        ]
    )


def _get_existing_unit_refs(
    *,
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
    stage: str,
) -> list[str]:
    return artifact_repository.find("unit", {"source_ref_id": source_ref_id, "stage": stage})


def _render_document_summary(payload: DocumentPayload) -> str:
    preview_items = [f"- {summary}" for summary in payload.unit_summaries if summary.strip()]
    preview_text = "\n".join(preview_items) if preview_items else "- 추출된 본문이 없습니다."
    page_count_line = (
        f"- 감지된 페이지 수: {payload.page_count}"
        if payload.page_count > 0
        else "- 감지된 페이지 수: 확인되지 않음"
    )
    excerpt_line = ""
    if payload.markdown_excerpt is not None and payload.markdown_excerpt.strip():
        excerpt_line = f"\n- 문서 미리보기:\n{payload.markdown_excerpt[:500]}"
    return (
        "문서 분석을 완료했습니다.\n"
        f"- 문서 유형: {payload.source_type}\n"
        f"- 파일명: {payload.file_name}\n"
        f"{page_count_line}\n"
        f"- 추출된 단위 수: {payload.unit_count}\n"
        "- 추출된 핵심 내용:\n"
        f"{preview_text}"
        f"{excerpt_line}"
    )
