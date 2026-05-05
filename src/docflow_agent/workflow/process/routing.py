from docflow_agent.workflow.state import WorkflowState


def route_selected_flow(state: WorkflowState) -> str:
    return state["flow"]


def route_mail_approval(state: WorkflowState) -> str:
    decision = state.get("pending_human_decision")
    if decision is not None and decision.get("selected") is None:
        return "awaiting_approval"

    selected = next(
        (
            item["selected"]
            for item in state.get("human_decisions", [])
            if item["decision_id"] == "approve_send_mail"
        ),
        None,
    )
    if selected == "approve":
        return "approved"
    return "rejected"
