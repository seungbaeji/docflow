from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.usecases.document import (
    build_context,
    build_payload as build_payload_from_parts,
    build_question_payload,
    render_summary,
)
from docflow_agent.workflow.document.parse import parse_units
from docflow_agent.workflow.document.support import (
    find_artifact_refs,
    load_latest_parsed_document,
    load_parsed_unit_payload,
    load_source_payload,
)

PdfParser = Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument]


def build_payload(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: PdfParser,
) -> DocumentPayload:
    source = load_source_payload(artifact_repository, source_ref_id)
    parsed_unit_ref_ids = parse_units(
        artifact_repository,
        source_ref_id=source_ref_id,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    parsed_units = [load_parsed_unit_payload(artifact_repository, ref_id) for ref_id in parsed_unit_ref_ids]
    parsed_document = load_latest_parsed_document(artifact_repository, source_ref_id)
    analyzed_refs = find_artifact_refs(
        artifact_repository,
        kind="analysis",
        filters={"source_ref_id": source_ref_id, "stage": "analyzed"},
    )
    analysis_value = artifact_repository.load("analysis", analyzed_refs[-1]) if analyzed_refs else None
    return build_payload_from_parts(
        source_ref_id=source_ref_id,
        source=source,
        parsed_document=parsed_document,
        parsed_units=parsed_units,
        parsed_unit_ref_ids=parsed_unit_ref_ids,
        analysis=analysis_value if isinstance(analysis_value, dict) else None,
    )


def build_context_by_ref(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: PdfParser,
) -> str:
    return build_context(
        build_payload(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )
    )


def summarize_ref(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: PdfParser,
) -> str:
    return render_summary(
        build_payload(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        )
    )


def answer_question_about_ref(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
    question: str,
    llm_gateway: DocumentLlmPort | None,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: PdfParser,
) -> str:
    payload = build_payload(
        artifact_repository,
        source_ref_id=source_ref_id,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    if llm_gateway is None:
        return render_summary(payload)
    question_payload = build_question_payload(question, payload)
    return llm_gateway.ask_document_question(
        question=question_payload.question,
        payload=asdict(question_payload.document),
    )
