from docflow_agent.workflow.document_workflow import (
    invoke_document_workflow,
    workflow_state_to_response,
)


def main() -> None:
    state = invoke_document_workflow(
        user_input="엑셀에서 미정산 건을 찾아 메일로 보내줘",
        human_decisions=[
            {
                "decision_id": "approve_send_mail",
                "kind": "approve",
                "message": "Approve sending the generated mail draft?",
                "options": ["approve", "reject"],
                "selected": "approve",
                "payload": None,
            }
        ],
    )
    print(workflow_state_to_response(state))
