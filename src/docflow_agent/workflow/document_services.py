from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Literal, TypedDict

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient, extract_pdf_document
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.boundary.external import VectorStoreDocument, WorkflowRunRecord
from docflow_agent.types.value.document import (
    AnalysisPayload,
    BundlePayload,
    CategorizedUnitPayload,
    DatasetPayload,
    DocumentPayload,
    MailResultPayload,
    ParsedDocumentPayload,
    ParsedUnitPayload,
    SourcePayload,
    UploadPayload,
)
from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.usecases.document import (
    analyze_bundle_payload,
    build_dataset_payload,
    build_document_context,
    build_document_payload as build_document_payload_from_parts,
    build_document_question_payload,
    build_mail_draft_payload,
    build_mail_result_payload,
    build_source_payload_from_prompt,
    build_source_payload_from_upload,
    categorize_unit_payloads,
    combine_unit_payloads,
    parse_source_payload,
    render_document_summary,
)


class DocumentWorkflowServices(TypedDict):
    stage_upload: Callable[[str, str, str, int], str]
    load_source: Callable[[str], str]
    source_from_upload: Callable[[str], str]
    parse_units: Callable[[str], list[str]]
    categorize_units: Callable[[list[str]], list[str]]
    combine_bundle: Callable[[list[str]], str]
    analyze: Callable[[str], UsecaseOutcome]
    filter_dataset: Callable[[str], str]
    compose_mail: Callable[[str], str]
    send_mail: Callable[[str], UsecaseOutcome]
    reject_send_mail: Callable[[str | None], UsecaseOutcome]
    handle_unknown: Callable[[str], UsecaseOutcome]
    build_document_payload: Callable[[str], DocumentPayload]
    build_document_context: Callable[[str], str]
    summarize_source_ref: Callable[[str], str]
    answer_question_about_source_ref: Callable[[str, str], str]


PdfParser = Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument]


def bind_document_workflow_services(
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: PdfParser = extract_pdf_document,
) -> DocumentWorkflowServices:
    def stage_upload(file_name: str, stored_path: str, content_type: str, size_bytes: int) -> str:
        return artifact_repository.save(
            kind="upload",
            value={
                "upload_id": None,
                "file_name": file_name,
                "stored_path": stored_path,
                "content_type": content_type,
                "size_bytes": size_bytes,
            },
            metadata={"stage": "uploaded"},
        )

    def load_source(user_input: str) -> str:
        payload = build_source_payload_from_prompt(user_input)
        return _save_source_payload(artifact_repository, payload, stage="loaded")

    def source_from_upload(upload_id: str) -> str:
        upload = _load_upload_payload(artifact_repository, upload_id)
        payload = build_source_payload_from_upload(upload)
        return _save_source_payload(
            artifact_repository,
            payload,
            stage="uploaded_source",
            metadata={"upload_id": upload_id},
        )

    def parse_units(source_ref_id: str) -> list[str]:
        source = _load_source_payload(artifact_repository, source_ref_id)
        existing_refs = _find_artifact_refs(
            artifact_repository,
            kind="unit",
            filters={"source_ref_id": source_ref_id, "stage": "parsed"},
        )
        if existing_refs:
            return existing_refs

        parsed_document, parsed_units = parse_source_payload(
            source,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )
        parsed_ref_id: str | None = None
        if parsed_document is not None:
            parsed_ref_id = artifact_repository.save(
                kind="analysis",
                value=asdict(parsed_document),
                metadata={"source_ref_id": source_ref_id, "stage": "pdf_parsed"},
            )
        unit_ref_ids: list[str] = []
        for unit in parsed_units:
            metadata: dict[str, object] = {"source_ref_id": source_ref_id, "stage": "parsed"}
            if unit.page_number is not None:
                metadata["page_number"] = unit.page_number
            if parsed_ref_id is not None:
                metadata["parsed_ref_id"] = parsed_ref_id
            unit_ref_ids.append(
                artifact_repository.save(
                    kind="unit",
                    value={
                        **asdict(unit),
                        "source_ref_id": source_ref_id,
                        "parsed_ref_id": parsed_ref_id,
                    },
                    metadata=metadata,
                )
            )
        return unit_ref_ids

    def categorize_units(unit_ref_ids: list[str]) -> list[str]:
        categorized_refs: list[str] = []
        units = [_load_parsed_unit_payload(artifact_repository, unit_ref_id) for unit_ref_id in unit_ref_ids]
        categorized_units = categorize_unit_payloads(units)
        for parent_ref_id, categorized_unit in zip(unit_ref_ids, categorized_units, strict=True):
            source_ref_id = _load_source_ref_from_unit(artifact_repository, parent_ref_id)
            categorized_refs.append(
                artifact_repository.save(
                    kind="unit",
                    value={
                        **asdict(categorized_unit),
                        "source_ref_id": source_ref_id,
                    },
                    metadata={
                        "parent_unit_ref_id": parent_ref_id,
                        "source_ref_id": source_ref_id,
                        "stage": "categorized",
                    },
                )
            )
        return categorized_refs

    def combine_bundle(unit_ref_ids: list[str]) -> str:
        units = [_load_categorized_unit_payload(artifact_repository, unit_ref_id) for unit_ref_id in unit_ref_ids]
        source_ref_id = _load_source_ref_from_unit(artifact_repository, unit_ref_ids[0]) if unit_ref_ids else None
        bundle = combine_unit_payloads(units, unit_ref_ids=unit_ref_ids, source_ref_id=source_ref_id)
        return artifact_repository.save(
            kind="bundle",
            value=asdict(bundle),
            metadata={"stage": "combined", "source_ref_id": source_ref_id},
        )

    def analyze(bundle_ref_id: str) -> UsecaseOutcome:
        bundle = _load_bundle_payload(artifact_repository, bundle_ref_id)
        analysis = analyze_bundle_payload(bundle)
        analysis_ref_id = artifact_repository.save(
            kind="analysis",
            value={**asdict(analysis), "bundle_ref_id": bundle_ref_id},
            metadata={
                "bundle_ref_id": bundle_ref_id,
                "source_ref_id": bundle.source_ref_id,
                "stage": "analyzed",
            },
        )
        _save_workflow_run(
            workflow_run_store,
            record_id=analysis_ref_id,
            status="analyzed",
            artifact_refs=[bundle_ref_id, analysis_ref_id],
            metadata={"bundle_ref_id": bundle_ref_id, "category": bundle.category},
        )
        _upsert_vector_document(
            vector_store,
            document_id=analysis_ref_id,
            text=f"Analysis for {bundle_ref_id} category={bundle.category}",
            metadata={"bundle_ref_id": bundle_ref_id, "kind": "analysis"},
        )
        return UsecaseOutcome(
            ref_id=analysis_ref_id,
            message=f"Document processed with {len(bundle.unit_ref_ids)} categorized units.",
        )

    def filter_dataset(bundle_ref_id: str) -> str:
        dataset = build_dataset_payload()
        return artifact_repository.save(
            kind="dataset",
            value={**asdict(dataset), "bundle_ref_id": bundle_ref_id},
            metadata={"bundle_ref_id": bundle_ref_id, "stage": "filtered"},
        )

    def compose_mail(dataset_ref_id: str) -> str:
        dataset = _load_dataset_payload(artifact_repository, dataset_ref_id)
        draft = build_mail_draft_payload(dataset, llm_gateway=llm_gateway)
        return artifact_repository.save(
            kind="draft",
            value={**asdict(draft), "dataset_ref_id": dataset_ref_id},
            metadata={"dataset_ref_id": dataset_ref_id, "stage": "composed"},
        )

    def send_mail(draft_ref_id: str) -> UsecaseOutcome:
        result = build_mail_result_payload(draft_ref_id, status="sent")
        result_ref_id = artifact_repository.save(
            kind="result",
            value=asdict(result),
            metadata={"draft_ref_id": draft_ref_id, "stage": "sent"},
        )
        _save_workflow_run(
            workflow_run_store,
            record_id=result_ref_id,
            status="sent",
            artifact_refs=[draft_ref_id, result_ref_id],
            metadata={"draft_ref_id": draft_ref_id},
        )
        return UsecaseOutcome(ref_id=result_ref_id, message="Mail sent after approval.")

    def reject_send_mail(draft_ref_id: str | None) -> UsecaseOutcome:
        result = build_mail_result_payload(draft_ref_id, status="rejected")
        result_ref_id = artifact_repository.save(
            kind="result",
            value=asdict(result),
            metadata={"draft_ref_id": draft_ref_id, "stage": "rejected"},
        )
        _save_workflow_run(
            workflow_run_store,
            record_id=result_ref_id,
            status="rejected",
            artifact_refs=[ref for ref in [draft_ref_id, result_ref_id] if ref is not None],
            metadata={"draft_ref_id": draft_ref_id},
        )
        return UsecaseOutcome(ref_id=result_ref_id, message="User rejected mail sending.")

    def handle_unknown(user_input: str) -> UsecaseOutcome:
        result_ref_id = artifact_repository.save(
            kind="result",
            value={"prompt": user_input, "status": "unknown"},
            metadata={"stage": "unknown"},
        )
        _save_workflow_run(
            workflow_run_store,
            record_id=result_ref_id,
            status="unknown",
            artifact_refs=[result_ref_id],
            metadata={"prompt": user_input},
        )
        return UsecaseOutcome(
            ref_id=result_ref_id,
            message="Unable to determine a supported workflow for the request.",
        )

    def build_document_payload(source_ref_id: str) -> DocumentPayload:
        source = _load_source_payload(artifact_repository, source_ref_id)
        parsed_unit_ref_ids = parse_units(source_ref_id)
        parsed_units = [_load_parsed_unit_payload(artifact_repository, ref_id) for ref_id in parsed_unit_ref_ids]
        parsed_document = _load_latest_parsed_document(artifact_repository, source_ref_id)
        analyzed_refs = _find_artifact_refs(
            artifact_repository,
            kind="analysis",
            filters={"source_ref_id": source_ref_id, "stage": "analyzed"},
        )
        analysis_value = artifact_repository.load("analysis", analyzed_refs[-1]) if analyzed_refs else None
        return build_document_payload_from_parts(
            source_ref_id=source_ref_id,
            source=source,
            parsed_document=parsed_document,
            parsed_units=parsed_units,
            parsed_unit_ref_ids=parsed_unit_ref_ids,
            analysis=analysis_value if isinstance(analysis_value, dict) else None,
        )

    def build_document_context_by_ref(source_ref_id: str) -> str:
        return build_document_context(build_document_payload(source_ref_id))

    def summarize_source_ref(source_ref_id: str) -> str:
        return render_document_summary(build_document_payload(source_ref_id))

    def answer_question_about_source_ref(source_ref_id: str, question: str) -> str:
        payload = build_document_payload(source_ref_id)
        if llm_gateway is None:
            return render_document_summary(payload)
        question_payload = build_document_question_payload(question, payload)
        return llm_gateway.ask_document_question(
            question=question_payload.question,
            payload=asdict(question_payload.document),
        )

    return {
        "stage_upload": stage_upload,
        "load_source": load_source,
        "source_from_upload": source_from_upload,
        "parse_units": parse_units,
        "categorize_units": categorize_units,
        "combine_bundle": combine_bundle,
        "analyze": analyze,
        "filter_dataset": filter_dataset,
        "compose_mail": compose_mail,
        "send_mail": send_mail,
        "reject_send_mail": reject_send_mail,
        "handle_unknown": handle_unknown,
        "build_document_payload": build_document_payload,
        "build_document_context": build_document_context_by_ref,
        "summarize_source_ref": summarize_source_ref,
        "answer_question_about_source_ref": answer_question_about_source_ref,
    }


def _save_source_payload(
    artifact_repository: ArtifactRepository,
    payload: SourcePayload,
    *,
    stage: str,
    metadata: dict[str, object] | None = None,
) -> str:
    return artifact_repository.save(
        kind="source",
        value=asdict(payload),
        metadata={"stage": stage, **(metadata or {})},
    )


def _load_upload_payload(artifact_repository: ArtifactRepository, upload_id: str) -> UploadPayload:
    value = artifact_repository.load("upload", upload_id)
    return UploadPayload(
        upload_id=upload_id,
        file_name=str(value["file_name"]),
        stored_path=str(value["stored_path"]),
        content_type=str(value["content_type"]),
        size_bytes=int(value["size_bytes"]),
    )


def _load_source_payload(artifact_repository: ArtifactRepository, source_ref_id: str) -> SourcePayload:
    value = artifact_repository.load("source", source_ref_id)
    source_type = str(value.get("source_type", "generic"))
    if source_type == "pdf":
        normalized_source_type: Literal["pdf", "excel", "generic"] = "pdf"
    elif source_type == "excel":
        normalized_source_type = "excel"
    else:
        normalized_source_type = "generic"
    return SourcePayload(
        prompt=str(value.get("prompt", "")),
        source_type=normalized_source_type,
        file_path=str(value["file_path"]) if value.get("file_path") is not None else None,
        file_name=str(value["file_name"]) if value.get("file_name") is not None else None,
        content_type=str(value["content_type"]) if value.get("content_type") is not None else None,
        uploaded=bool(value.get("uploaded", False)),
    )


def _load_parsed_unit_payload(artifact_repository: ArtifactRepository, unit_ref_id: str) -> ParsedUnitPayload:
    value = artifact_repository.load("unit", unit_ref_id)
    return ParsedUnitPayload(
        name=str(value["name"]),
        prompt=str(value["prompt"]),
        page_number=int(value["page_number"]) if value.get("page_number") is not None else None,
        content=str(value["content"]) if value.get("content") is not None else None,
        element_count=int(value["element_count"]) if value.get("element_count") is not None else None,
    )


def _load_categorized_unit_payload(
    artifact_repository: ArtifactRepository,
    unit_ref_id: str,
) -> CategorizedUnitPayload:
    value = artifact_repository.load("unit", unit_ref_id)
    return CategorizedUnitPayload(
        name=str(value["name"]),
        prompt=str(value["prompt"]),
        category=str(value["category"]),
        page_number=int(value["page_number"]) if value.get("page_number") is not None else None,
        content=str(value["content"]) if value.get("content") is not None else None,
        element_count=int(value["element_count"]) if value.get("element_count") is not None else None,
    )


def _load_bundle_payload(artifact_repository: ArtifactRepository, bundle_ref_id: str) -> BundlePayload:
    value = artifact_repository.load("bundle", bundle_ref_id)
    return from_docflow_bundle(value)


def from_docflow_bundle(value: dict[str, object]) -> BundlePayload:
    unit_ref_ids = value.get("unit_ref_ids", [])
    if not isinstance(unit_ref_ids, list):
        unit_ref_ids = []
    return BundlePayload(
        category=str(value.get("category", "general")),
        unit_ref_ids=[str(item) for item in unit_ref_ids],
        source_ref_id=str(value["source_ref_id"]) if value.get("source_ref_id") is not None else None,
    )


def _load_dataset_payload(artifact_repository: ArtifactRepository, dataset_ref_id: str) -> DatasetPayload:
    value = artifact_repository.load("dataset", dataset_ref_id)
    records = value.get("records", [])
    return DatasetPayload(records=records if isinstance(records, list) else [])


def _load_source_ref_from_unit(artifact_repository: ArtifactRepository, unit_ref_id: str) -> str:
    value = artifact_repository.load("unit", unit_ref_id)
    source_ref_id = value.get("source_ref_id")
    if not isinstance(source_ref_id, str):
        raise KeyError(f"Unit {unit_ref_id} does not contain a source_ref_id")
    return source_ref_id


def _find_artifact_refs(
    artifact_repository: ArtifactRepository,
    *,
    kind: str,
    filters: dict[str, object],
) -> list[str]:
    return artifact_repository.find(kind, filters)


def _load_latest_parsed_document(
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
) -> ParsedDocumentPayload | None:
    parsed_refs = _find_artifact_refs(
        artifact_repository,
        kind="analysis",
        filters={"source_ref_id": source_ref_id, "stage": "pdf_parsed"},
    )
    if not parsed_refs:
        return None
    value = artifact_repository.load("analysis", parsed_refs[-1])
    return ParsedDocumentPayload(
        file_name=str(value.get("file_name", "")),
        page_count=int(value.get("page_count", 0)),
        markdown=str(value["markdown"]) if value.get("markdown") is not None else None,
        text=str(value["text"]) if value.get("text") is not None else None,
    )

def _save_workflow_run(
    workflow_run_store: WorkflowRunStore | None,
    *,
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
    vector_store: VectorStorePort | None,
    *,
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
