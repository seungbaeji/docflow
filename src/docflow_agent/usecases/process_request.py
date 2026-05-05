from __future__ import annotations

from collections.abc import Callable

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.value.workflow import HumanDecision
from docflow_agent.workflow.process import invoke_workflow
from docflow_agent.workflow.process.factory import create_workflow
from docflow_agent.workflow.process.graph import state_to_response
from docflow_agent.workflow.state import WorkflowState


def process_request(
    *,
    artifact_repository: ArtifactRepository,
    workflow_run_store: WorkflowRunStore,
    workflow_queue: WorkflowQueuePort,
    vector_store: VectorStorePort,
    llm_gateway: DocumentLlmPort,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument],
    user_input: str,
    human_decisions: list[HumanDecision] | None,
) -> WorkflowState:
    workflow = create_workflow(
        artifact_repository=artifact_repository,
        workflow_run_store=workflow_run_store,
        workflow_queue=workflow_queue,
        vector_store=vector_store,
        llm_gateway=llm_gateway,
        pdf_client=pdf_client,
        pdf_parser=pdf_parser,
    )
    return invoke_workflow(
        user_input=user_input,
        human_decisions=human_decisions,
        workflow=workflow,
    )


__all__ = ["process_request", "state_to_response"]
