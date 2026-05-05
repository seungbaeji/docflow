from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import cast

from docflow_agent.errors import (
    DocflowError,
    EcmRequestError,
    EcmResponseError,
    MailIntegrationError,
    UnsupportedCategoryError,
    UnsupportedLlmProviderError,
    UnsupportedSourceKindError,
)
from docflow_agent.workflow.state import HumanDecision
from docflow_agent.workflow.document_workflow import (
    invoke_document_workflow,
    workflow_state_to_response,
)

router = APIRouter()


class HumanDecisionRequest(BaseModel):
    decision_id: str
    kind: str
    message: str
    options: list[str]
    selected: str | None = None
    payload: dict[str, object] | None = None


class ProcessRequest(BaseModel):
    user_input: str
    human_decisions: list[HumanDecisionRequest] | None = None


@router.post("/process")
def process(request: ProcessRequest) -> dict[str, object]:
    try:
        human_decisions = (
            cast(list[HumanDecision], [decision.model_dump() for decision in request.human_decisions])
            if request.human_decisions
            else None
        )
        state = invoke_document_workflow(
            user_input=request.user_input,
            human_decisions=human_decisions,
        )
    except (UnsupportedSourceKindError, UnsupportedCategoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (EcmRequestError, EcmResponseError, MailIntegrationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except UnsupportedLlmProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except DocflowError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return workflow_state_to_response(state)
