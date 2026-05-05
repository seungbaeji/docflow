from __future__ import annotations

from dataclasses import asdict

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.usecases.document import (
    build_context,
    build_payload as build_payload_from_parts,
    build_question_payload,
    render_summary,
)
from docflow_agent.workflow.document.support import (
    load_latest_analysis_value,
    load_latest_parsed_document,
    load_parsed_unit_ref_ids,
    load_parsed_unit_payload,
    load_source_payload,
)


def build_payload(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
) -> DocumentPayload:
    source = load_source_payload(artifact_repository, source_ref_id)
    parsed_unit_ref_ids = load_parsed_unit_ref_ids(artifact_repository, source_ref_id)
    parsed_units = [load_parsed_unit_payload(artifact_repository, ref_id) for ref_id in parsed_unit_ref_ids]
    parsed_document = load_latest_parsed_document(artifact_repository, source_ref_id)
    return build_payload_from_parts(
        source_ref_id=source_ref_id,
        source=source,
        parsed_document=parsed_document,
        parsed_units=parsed_units,
        parsed_unit_ref_ids=parsed_unit_ref_ids,
        analysis=load_latest_analysis_value(artifact_repository, source_ref_id),
    )


def build_context_by_ref(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
) -> str:
    return build_context(
        build_payload(
            artifact_repository,
            source_ref_id=source_ref_id,
        )
    )


def summarize_ref(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
) -> str:
    return render_summary(
        build_payload(
            artifact_repository,
            source_ref_id=source_ref_id,
        )
    )


def answer_question_about_ref(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
    question: str,
    llm_gateway: DocumentLlmPort | None,
) -> str:
    payload = build_payload(
        artifact_repository,
        source_ref_id=source_ref_id,
    )
    if llm_gateway is None:
        return render_summary(payload)
    question_payload = build_question_payload(question, payload)
    return llm_gateway.ask_document_question(
        question=question_payload.question,
        payload=asdict(question_payload.document),
    )
