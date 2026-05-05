"""Workflow assembly helpers for process-style document requests.

These helpers bind explicit dependencies to the process workflow graph.
They are part of the workflow layer, but they consume only already-assembled
dependencies and never reach back into `bootstrap`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source
from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.workflow.process.graph import build_workflow


def build_runtime(
    *,
    workflow_run_store: WorkflowRunStore,
    workflow_queue: WorkflowQueuePort,
) -> WorkflowRuntime:
    """Create the runtime helper shared by process workflow nodes.

    The runtime bundles cross-cutting orchestration services such as workflow
    run recording and queue publication. It does not contain business logic.
    """
    return WorkflowRuntime(
        workflow_run_store=workflow_run_store,
        workflow_queue=workflow_queue,
    )


def create_workflow(
    *,
    artifact_repository: ArtifactRepository,
    workflow_run_store: WorkflowRunStore,
    workflow_queue: WorkflowQueuePort,
    vector_store: VectorStorePort,
    llm_gateway: DocumentLlmPort,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument],
    workflow_runtime: WorkflowRuntime | None = None,
) -> Any:
    """Build the compiled process workflow from concrete orchestration deps.

    This function is the composition point for the main process graph. It
    binds repository-backed workflow helpers to the graph's node callables and
    returns a compiled LangGraph workflow ready to invoke.
    """
    active_runtime = workflow_runtime or build_runtime(
        workflow_run_store=workflow_run_store,
        workflow_queue=workflow_queue,
    )
    return build_workflow(
        workflow_runtime=active_runtime,
        load_source=lambda prompt: document_source.load_source(
            artifact_repository,
            user_input=prompt,
        ),
        parse_units=lambda source_ref_id: document_parse.parse_units(
            artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=pdf_client,
            pdf_parser=pdf_parser,
        ),
        categorize_units=lambda unit_ref_ids: document_parse.categorize_units(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        combine_bundle=lambda unit_ref_ids: document_parse.combine_bundle(
            artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        analyze=lambda bundle_ref_id: document_mail.analyze(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=workflow_run_store,
            vector_store=vector_store,
        ),
        filter_dataset=lambda bundle_ref_id: document_mail.filter_dataset(
            artifact_repository,
            bundle_ref_id=bundle_ref_id,
        ),
        compose_mail=lambda dataset_ref_id: document_mail.compose_mail(
            artifact_repository,
            dataset_ref_id=dataset_ref_id,
            llm_gateway=llm_gateway,
        ),
        send_mail=lambda draft_ref_id: document_mail.send_mail(
            artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=workflow_run_store,
        ),
        reject_send_mail=lambda draft_ref_id: document_mail.reject_send_mail(
            artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=workflow_run_store,
        ),
        handle_unknown=lambda prompt: document_mail.handle_unknown(
            artifact_repository,
            user_input=prompt,
            workflow_run_store=workflow_run_store,
        ),
    )
