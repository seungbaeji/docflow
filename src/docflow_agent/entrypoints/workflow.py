from __future__ import annotations

import argparse

from docflow_agent.bootstrap import get_container
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source
from docflow_agent.workflow.document_workflow import (
    create_document_workflow,
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.workflow.state import HumanDecision


def _build_human_decisions(approve_send_mail: str | None) -> list[HumanDecision] | None:
    if approve_send_mail is None:
        return None
    return [
        {
            "decision_id": "approve_send_mail",
            "kind": "approve",
            "message": "Approve sending the generated mail draft?",
            "options": ["approve", "reject"],
            "selected": approve_send_mail,
            "payload": None,
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the document workflow from a prompt.")
    parser.add_argument(
        "user_input",
        nargs="?",
        default="엑셀 문서를 분석해줘",
        help="Prompt that tells the workflow what document flow to run.",
    )
    parser.add_argument(
        "--approve-send-mail",
        choices=["approve", "reject"],
        help="Inject a human decision for the mail approval step.",
    )
    args = parser.parse_args()

    container = get_container()
    workflow_runtime = WorkflowRuntime(
        workflow_run_store=container.workflow_run_store,
        workflow_queue=container.workflow_queue,
    )
    workflow = create_document_workflow(
        artifact_repository=container.artifact_repository,
        workflow_runtime=workflow_runtime,
        load_source=lambda user_input: document_source.load_source(
            container.artifact_repository,
            user_input=user_input,
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
        handle_unknown=lambda user_input: document_mail.handle_unknown(
            container.artifact_repository,
            user_input=user_input,
            workflow_run_store=container.workflow_run_store,
        ),
    )
    state = invoke_document_workflow(
        user_input=args.user_input,
        workflow=workflow,
        human_decisions=_build_human_decisions(args.approve_send_mail),
    )
    print(workflow_state_to_response(state))
