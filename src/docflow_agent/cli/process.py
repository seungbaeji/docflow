import argparse

from docflow_agent.workflow.document_workflow import (
    invoke_document_workflow,
    workflow_state_to_response,
)
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

    state = invoke_document_workflow(
        user_input=args.user_input,
        human_decisions=_build_human_decisions(args.approve_send_mail),
    )
    print(workflow_state_to_response(state))
