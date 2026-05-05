from __future__ import annotations

from dataclasses import asdict

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.usecases.document import (
    analyze_bundle_payload,
    build_dataset_payload,
    build_mail_draft_payload,
    build_mail_result_payload,
)
from docflow_agent.workflow.document.support import (
    load_bundle_payload,
    load_dataset_payload,
    save_workflow_run,
    upsert_vector_document,
)


def analyze(
    artifact_repository: ArtifactRepository,
    *,
    bundle_ref_id: str,
    workflow_run_store: WorkflowRunStore | None,
    vector_store: VectorStorePort | None,
) -> UsecaseOutcome:
    bundle = load_bundle_payload(artifact_repository, bundle_ref_id)
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
    save_workflow_run(
        workflow_run_store,
        record_id=analysis_ref_id,
        status="analyzed",
        artifact_refs=[bundle_ref_id, analysis_ref_id],
        metadata={"bundle_ref_id": bundle_ref_id, "category": bundle.category},
    )
    upsert_vector_document(
        vector_store,
        document_id=analysis_ref_id,
        text=f"Analysis for {bundle_ref_id} category={bundle.category}",
        metadata={"bundle_ref_id": bundle_ref_id, "kind": "analysis"},
    )
    return UsecaseOutcome(
        ref_id=analysis_ref_id,
        message=f"Document processed with {len(bundle.unit_ref_ids)} categorized units.",
    )


def filter_dataset(artifact_repository: ArtifactRepository, *, bundle_ref_id: str) -> str:
    dataset = build_dataset_payload()
    return artifact_repository.save(
        kind="dataset",
        value={**asdict(dataset), "bundle_ref_id": bundle_ref_id},
        metadata={"bundle_ref_id": bundle_ref_id, "stage": "filtered"},
    )


def compose_mail(
    artifact_repository: ArtifactRepository,
    *,
    dataset_ref_id: str,
    llm_gateway: DocumentLlmPort | None,
) -> str:
    dataset = load_dataset_payload(artifact_repository, dataset_ref_id)
    draft = build_mail_draft_payload(dataset, llm_gateway=llm_gateway)
    return artifact_repository.save(
        kind="draft",
        value={**asdict(draft), "dataset_ref_id": dataset_ref_id},
        metadata={"dataset_ref_id": dataset_ref_id, "stage": "composed"},
    )


def send_mail(
    artifact_repository: ArtifactRepository,
    *,
    draft_ref_id: str,
    workflow_run_store: WorkflowRunStore | None,
) -> UsecaseOutcome:
    result = build_mail_result_payload(draft_ref_id, status="sent")
    result_ref_id = artifact_repository.save(
        kind="result",
        value=asdict(result),
        metadata={"draft_ref_id": draft_ref_id, "stage": "sent"},
    )
    save_workflow_run(
        workflow_run_store,
        record_id=result_ref_id,
        status="sent",
        artifact_refs=[draft_ref_id, result_ref_id],
        metadata={"draft_ref_id": draft_ref_id},
    )
    return UsecaseOutcome(ref_id=result_ref_id, message="Mail sent after approval.")


def reject_send_mail(
    artifact_repository: ArtifactRepository,
    *,
    draft_ref_id: str | None,
    workflow_run_store: WorkflowRunStore | None,
) -> UsecaseOutcome:
    result = build_mail_result_payload(draft_ref_id, status="rejected")
    result_ref_id = artifact_repository.save(
        kind="result",
        value=asdict(result),
        metadata={"draft_ref_id": draft_ref_id, "stage": "rejected"},
    )
    save_workflow_run(
        workflow_run_store,
        record_id=result_ref_id,
        status="rejected",
        artifact_refs=[ref for ref in [draft_ref_id, result_ref_id] if ref is not None],
        metadata={"draft_ref_id": draft_ref_id},
    )
    return UsecaseOutcome(ref_id=result_ref_id, message="User rejected mail sending.")


def handle_unknown(
    artifact_repository: ArtifactRepository,
    *,
    user_input: str,
    workflow_run_store: WorkflowRunStore | None,
) -> UsecaseOutcome:
    result_ref_id = artifact_repository.save(
        kind="result",
        value={"prompt": user_input, "status": "unknown"},
        metadata={"stage": "unknown"},
    )
    save_workflow_run(
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
