from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient, extract_pdf_document
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.workflow.document import chat as chat_workflow
from docflow_agent.workflow.document import mail as mail_workflow
from docflow_agent.workflow.document import parse as parse_workflow
from docflow_agent.workflow.document import source as source_workflow


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
    return {
        "stage_upload": lambda file_name, stored_path, content_type, size_bytes: source_workflow.stage_upload(
            artifact_repository,
            file_name=file_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=size_bytes,
        ),
        "load_source": lambda user_input: source_workflow.load_source(
            artifact_repository,
            user_input=user_input,
        ),
        "source_from_upload": lambda upload_id: source_workflow.source_from_upload(
            artifact_repository,
            upload_id=upload_id,
        ),
        "parse_units": lambda source_ref_id: parse_workflow.parse_units(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        "categorize_units": lambda unit_ref_ids: parse_workflow.categorize_units(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "combine_bundle": lambda unit_ref_ids: parse_workflow.combine_bundle(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "analyze": lambda bundle_ref_id: mail_workflow.analyze(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
        ),
        "filter_dataset": lambda bundle_ref_id: mail_workflow.filter_dataset(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
        ),
        "compose_mail": lambda dataset_ref_id: mail_workflow.compose_mail(
            artifact_repository,
            dataset_ref_id=dataset_ref_id,
            llm_gateway=llm_gateway,
        ),
        "send_mail": lambda draft_ref_id: mail_workflow.send_mail(
            artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=workflow_run_store,
        ),
        "reject_send_mail": lambda draft_ref_id: mail_workflow.reject_send_mail(
            artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=workflow_run_store,
        ),
        "handle_unknown": lambda user_input: mail_workflow.handle_unknown(
            artifact_repository,
            user_input=user_input,
            workflow_run_store=workflow_run_store,
        ),
        "build_document_payload": lambda source_ref_id: chat_workflow.build_document_payload(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        "build_document_context": lambda source_ref_id: chat_workflow.build_document_context_by_ref(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        "summarize_source_ref": lambda source_ref_id: chat_workflow.summarize_source_ref(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        "answer_question_about_source_ref": lambda source_ref_id, question: chat_workflow.answer_question_about_source_ref(
            artifact_repository,
            source_ref_id=source_ref_id,
            question=question,
            llm_gateway=llm_gateway,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
    }
