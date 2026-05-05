from __future__ import annotations

import argparse

from docflow_agent.bootstrap import get_container
from docflow_agent.types.value.workflow import HumanDecision
from docflow_agent.usecases.process_request import process_request, state_to_response


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
    state = process_request(
        artifact_repository=container.artifact_repository,
        workflow_run_store=container.workflow_run_store,
        workflow_queue=container.workflow_queue,
        vector_store=container.vector_store,
        llm_gateway=container.llm_gateway,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
        user_input=args.user_input,
        human_decisions=_build_human_decisions(args.approve_send_mail),
    )
    print(state_to_response(state))
