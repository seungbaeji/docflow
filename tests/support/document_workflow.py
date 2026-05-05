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
import docflow_agent.workflow.document.chat as document_chat
import docflow_agent.workflow.document.mail as document_mail
import docflow_agent.workflow.document.parse as document_parse
import docflow_agent.workflow.document.source as document_source


class DocumentWorkflowFunctionSet(TypedDict):
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
    build_payload: Callable[[str], DocumentPayload]
    build_context: Callable[[str], str]
    summarize_ref: Callable[[str], str]
    answer_question_about_ref: Callable[[str, str], str]


class DocumentWorkflowKwargs(TypedDict):
    load_source: Callable[[str], str]
    parse_units: Callable[[str], list[str]]
    categorize_units: Callable[[list[str]], list[str]]
    combine_bundle: Callable[[list[str]], str]
    analyze: Callable[[str], UsecaseOutcome]
    filter_dataset: Callable[[str], str]
    compose_mail: Callable[[str], str]
    send_mail: Callable[[str], UsecaseOutcome]
    reject_send_mail: Callable[[str | None], UsecaseOutcome]
    handle_unknown: Callable[[str], UsecaseOutcome]


def build_document_workflow_functions(
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument] = extract_pdf_document,
) -> DocumentWorkflowFunctionSet:
    return {
        "stage_upload": lambda file_name, stored_path, content_type, size_bytes: document_source.stage_upload(
            artifact_repository,
            file_name=file_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=size_bytes,
        ),
        "load_source": lambda user_input: document_source.load_source(
            artifact_repository,
            user_input=user_input,
        ),
        "source_from_upload": lambda upload_id: document_source.source_from_upload(
            artifact_repository,
            upload_id=upload_id,
        ),
        "parse_units": lambda source_ref_id: document_parse.parse_units(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        "categorize_units": lambda unit_ref_ids: document_parse.categorize_units(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "combine_bundle": lambda unit_ref_ids: document_parse.combine_bundle(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "analyze": lambda bundle_ref_id: document_mail.analyze(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
        ),
        "filter_dataset": lambda bundle_ref_id: document_mail.filter_dataset(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
        ),
        "compose_mail": lambda dataset_ref_id: document_mail.compose_mail(
            artifact_repository,
            dataset_ref_id=dataset_ref_id,
            llm_gateway=llm_gateway,
        ),
        "send_mail": lambda draft_ref_id: document_mail.send_mail(
            artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=workflow_run_store,
        ),
        "reject_send_mail": lambda draft_ref_id: document_mail.reject_send_mail(
            artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=workflow_run_store,
        ),
        "handle_unknown": lambda user_input: document_mail.handle_unknown(
            artifact_repository,
            user_input=user_input,
            workflow_run_store=workflow_run_store,
        ),
        "build_payload": lambda source_ref_id: document_chat.build_payload(
            artifact_repository,
            source_ref_id=source_ref_id,
        ),
        "build_context": lambda source_ref_id: document_chat.build_context_by_ref(
            artifact_repository,
            source_ref_id=source_ref_id,
        ),
        "summarize_ref": lambda source_ref_id: document_chat.summarize_ref(
            artifact_repository,
            source_ref_id=source_ref_id,
        ),
        "answer_question_about_ref": lambda source_ref_id, question: document_chat.answer_question_about_ref(
            artifact_repository,
            source_ref_id=source_ref_id,
            question=question,
            llm_gateway=llm_gateway,
        ),
    }


def build_document_workflow_kwargs(
    *,
    artifact_repository: ArtifactRepository,
    llm_gateway: DocumentLlmPort | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    vector_store: VectorStorePort | None = None,
    pdf_client: OpenDataLoaderPdfClient | None = None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument] = extract_pdf_document,
) -> DocumentWorkflowKwargs:
    functions = build_document_workflow_functions(
        artifact_repository=artifact_repository,
        llm_gateway=llm_gateway,
        workflow_run_store=workflow_run_store,
        vector_store=vector_store,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    return {
        "load_source": functions["load_source"],
        "parse_units": functions["parse_units"],
        "categorize_units": functions["categorize_units"],
        "combine_bundle": functions["combine_bundle"],
        "analyze": functions["analyze"],
        "filter_dataset": functions["filter_dataset"],
        "compose_mail": functions["compose_mail"],
        "send_mail": functions["send_mail"],
        "reject_send_mail": functions["reject_send_mail"],
        "handle_unknown": functions["handle_unknown"],
    }
