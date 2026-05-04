from __future__ import annotations

from docflow_agent.inbound.langgraph.state import FlowName, HumanDecision, WorkflowState

_DOCUMENT_KEYWORDS = ("excel", "엑셀", "document", "문서", "pdf", "image", "이미지", "settlement")
_MAIL_KEYWORDS = ("mail", "메일", "email", "send", "보내")


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


def route_flow(state: WorkflowState) -> FlowName:
    user_input = state.get("user_input", "")
    has_document_intent = _contains_any(user_input, _DOCUMENT_KEYWORDS)
    has_mail_intent = _contains_any(user_input, _MAIL_KEYWORDS)

    if has_document_intent and has_mail_intent:
        return "document_to_mail"
    if has_document_intent:
        return "document_process"
    return "unknown"


def has_human_decision(state: WorkflowState, decision_id: str) -> bool:
    return get_human_decision(state, decision_id) is not None


def get_human_decision(state: WorkflowState, decision_id: str) -> HumanDecision | None:
    for decision in state.get("human_decisions", []):
        if decision["decision_id"] == decision_id:
            return decision
    return None

