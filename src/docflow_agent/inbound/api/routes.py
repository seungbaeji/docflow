from fastapi import APIRouter, HTTPException, Request

from docflow_agent.errors import (
    DocflowError,
    EcmRequestError,
    EcmResponseError,
    LlmRequestError,
    MailIntegrationError,
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedCategoryError,
    UnsupportedLlmProviderError,
    UnsupportedSourceKindError,
)
from docflow_agent.types.boundary.api import ChatRequest, ChatResponse, ProcessRequest
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
    except LlmRequestError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (UnsupportedLlmProviderError, MissingLlmApiKeyError, MissingLlmDependencyError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except DocflowError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return workflow_state_to_response(state)


@router.post("/chat")
def chat(request: ChatRequest, app_request: Request) -> ChatResponse:
    try:
        container = app_request.app.state.container
        message = container.chat_usecase.respond(
            message=request.message,
            system_prompt=request.system_prompt,
            history=request.to_value_history(),
        )
    except LlmRequestError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (UnsupportedLlmProviderError, MissingLlmApiKeyError, MissingLlmDependencyError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except DocflowError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatResponse(
        message=message,
        provider=container.settings.llm.provider,
        model=container.settings.llm.model,
    )
