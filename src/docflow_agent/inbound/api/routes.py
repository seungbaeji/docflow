from fastapi import APIRouter, HTTPException

from docflow_agent.errors import (
    DocflowError,
    EcmRequestError,
    EcmResponseError,
    MailIntegrationError,
    UnsupportedCategoryError,
    UnsupportedLlmProviderError,
    UnsupportedSourceKindError,
)
from docflow_agent.types.boundary.api import ProcessRequest
from docflow_agent.workflow.document_workflow import (
    invoke_document_workflow,
    workflow_state_to_response,
)

router = APIRouter()


@router.post("/process")
def process(request: ProcessRequest) -> dict[str, object]:
    try:
        state = invoke_document_workflow(
            user_input=request.user_input,
            human_decisions=request.to_workflow_human_decisions(),
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
