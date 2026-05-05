import streamlit as st

from docflow_agent.errors import DocflowError
from docflow_agent.workflow.document_workflow import (
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.workflow.state import HumanDecision


def main() -> None:
    st.title("Document Workflow Demo")
    user_input = st.text_area(
        "Prompt",
        value="엑셀 문서를 분석해줘",
        help="Describe the document task you want the workflow to run.",
    )
    approval = st.selectbox(
        "Mail approval decision",
        options=["none", "approve", "reject"],
        help="Inject a human decision when testing the mail approval branch.",
    )

    if not st.button("Run workflow"):
        return

    try:
        human_decisions: list[HumanDecision] | None = None
        if approval != "none":
            human_decisions = [
                {
                    "decision_id": "approve_send_mail",
                    "kind": "approve",
                    "message": "Approve sending the generated mail draft?",
                    "options": ["approve", "reject"],
                    "selected": approval,
                    "payload": None,
                }
            ]
        state = invoke_document_workflow(
            user_input=user_input,
            human_decisions=human_decisions,
        )
    except DocflowError as exc:
        st.error(str(exc))
        return

    st.json(workflow_state_to_response(state))


if __name__ == "__main__":
    main()
