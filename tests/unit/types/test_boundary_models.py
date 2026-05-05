import pytest
from pydantic import ValidationError

from docflow_agent.types.boundary.api import ChatMessage, ChatRequest, HumanDecisionRequest
from docflow_agent.types.value.chat import ChatTurn
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


def test_chat_request_converts_history_to_value_objects() -> None:
    request = ChatRequest(
        message="next",
        system_prompt="Be concise.",
        history=[
            ChatMessage(role="user", content="hello"),
            ChatMessage(role="assistant", content="hi"),
        ],
    )

    assert request.to_value_history() == [
        ChatTurn(role="user", content="hello"),
        ChatTurn(role="assistant", content="hi"),
    ]
