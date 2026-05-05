import pytest
from pydantic import ValidationError

from docflow_agent.types.boundary.api import ChatRequest, HumanDecisionRequest
from docflow_agent.types.boundary.external import EcmSearchResponse


def test_human_decision_request_rejects_invalid_selected_option() -> None:
    with pytest.raises(ValidationError, match="selected must be one of options"):
        HumanDecisionRequest(
            decision_id="approve_send_mail",
            kind="approve",
            message="Approve sending the generated mail draft?",
            options=["approve", "reject"],
            selected="later",
        )


def test_ecm_search_response_rejects_invalid_document_payload() -> None:
    with pytest.raises(ValidationError, match="document_id"):
        EcmSearchResponse.model_validate(
            {
                "items": [
                    {
                        "name": "invoice.xlsx",
                        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    }
                ]
            }
        )


def test_chat_request_allows_session_id() -> None:
    request = ChatRequest(message="next", session_id="session-001")

    assert request.session_id == "session-001"
