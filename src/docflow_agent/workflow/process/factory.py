from __future__ import annotations

from typing import Any

from docflow_agent.bootstrap import AppContainer
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source
from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.workflow.process.graph import build_workflow


def build_runtime(container: AppContainer) -> WorkflowRuntime:
    return WorkflowRuntime(
        workflow_run_store=container.workflow_run_store,
        workflow_queue=container.workflow_queue,
    )


def create_workflow(
    container: AppContainer,
    *,
    workflow_runtime: WorkflowRuntime | None = None,
) -> Any:
    active_runtime = workflow_runtime or build_runtime(container)
    return build_workflow(
        workflow_runtime=active_runtime,
        load_source=lambda prompt: document_source.load_source(
            container.artifact_repository,
            user_input=prompt,
        ),
        parse_units=lambda source_ref_id: document_parse.parse_units(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        categorize_units=lambda unit_ref_ids: document_parse.categorize_units(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        combine_bundle=lambda unit_ref_ids: document_parse.combine_bundle(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        analyze=lambda bundle_ref_id: document_mail.analyze(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=container.workflow_run_store,
            vector_store=container.vector_store,
        ),
        filter_dataset=lambda bundle_ref_id: document_mail.filter_dataset(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
        ),
        compose_mail=lambda dataset_ref_id: document_mail.compose_mail(
            container.artifact_repository,
            dataset_ref_id=dataset_ref_id,
            llm_gateway=container.llm_gateway,
        ),
        send_mail=lambda draft_ref_id: document_mail.send_mail(
            container.artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=container.workflow_run_store,
        ),
        reject_send_mail=lambda draft_ref_id: document_mail.reject_send_mail(
            container.artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=container.workflow_run_store,
        ),
        handle_unknown=lambda prompt: document_mail.handle_unknown(
            container.artifact_repository,
            user_input=prompt,
            workflow_run_store=container.workflow_run_store,
        ),
    )
