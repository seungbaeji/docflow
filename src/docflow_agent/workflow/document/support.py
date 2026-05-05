from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.external import VectorStoreDocument, WorkflowRunRecord
from docflow_agent.types.value.document import (
    BundlePayload,
    CategorizedUnitPayload,
    DatasetPayload,
    ParsedDocumentPayload,
    ParsedUnitPayload,
    SourcePayload,
    UploadPayload,
)


def save_source_payload(
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


def load_upload_payload(artifact_repository: ArtifactRepository, upload_id: str) -> UploadPayload:
    value = artifact_repository.load("upload", upload_id)
    return UploadPayload(
        upload_id=upload_id,
        file_name=str(value["file_name"]),
        stored_path=str(value["stored_path"]),
        content_type=str(value["content_type"]),
        size_bytes=int(value["size_bytes"]),
    )


def load_source_payload(artifact_repository: ArtifactRepository, source_ref_id: str) -> SourcePayload:
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


def load_parsed_unit_payload(artifact_repository: ArtifactRepository, unit_ref_id: str) -> ParsedUnitPayload:
    value = artifact_repository.load("unit", unit_ref_id)
    return ParsedUnitPayload(
        name=str(value["name"]),
        prompt=str(value["prompt"]),
        page_number=int(value["page_number"]) if value.get("page_number") is not None else None,
        content=str(value["content"]) if value.get("content") is not None else None,
        element_count=int(value["element_count"]) if value.get("element_count") is not None else None,
    )


def load_categorized_unit_payload(
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


def load_bundle_payload(artifact_repository: ArtifactRepository, bundle_ref_id: str) -> BundlePayload:
    value = artifact_repository.load("bundle", bundle_ref_id)
    return bundle_from_record(value)


def bundle_from_record(value: dict[str, object]) -> BundlePayload:
    unit_ref_ids = value.get("unit_ref_ids", [])
    if not isinstance(unit_ref_ids, list):
        unit_ref_ids = []
    return BundlePayload(
        category=str(value.get("category", "general")),
        unit_ref_ids=[str(item) for item in unit_ref_ids],
        source_ref_id=str(value["source_ref_id"]) if value.get("source_ref_id") is not None else None,
    )


def load_dataset_payload(artifact_repository: ArtifactRepository, dataset_ref_id: str) -> DatasetPayload:
    value = artifact_repository.load("dataset", dataset_ref_id)
    records = value.get("records", [])
    return DatasetPayload(records=records if isinstance(records, list) else [])


def load_source_ref_from_unit(artifact_repository: ArtifactRepository, unit_ref_id: str) -> str:
    value = artifact_repository.load("unit", unit_ref_id)
    source_ref_id = value.get("source_ref_id")
    if not isinstance(source_ref_id, str):
        raise KeyError(f"Unit {unit_ref_id} does not contain a source_ref_id")
    return source_ref_id


def find_artifact_refs(
    artifact_repository: ArtifactRepository,
    *,
    kind: str,
    filters: dict[str, object],
) -> list[str]:
    return artifact_repository.find(kind, filters)


def load_latest_parsed_document(
    artifact_repository: ArtifactRepository,
    source_ref_id: str,
) -> ParsedDocumentPayload | None:
    parsed_refs = find_artifact_refs(
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


def save_workflow_run(
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


def upsert_vector_document(
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
