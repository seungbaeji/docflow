from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from docflow_agent.config.prompt import get_chat_system_prompt
from docflow_agent.errors import (
    DocflowError,
    EcmRequestError,
    EcmResponseError,
    LlmQuotaExceededError,
    LlmRateLimitError,
    LlmRequestError,
    MailIntegrationError,
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedCategoryError,
    UnsupportedLlmProviderError,
    UnsupportedSourceKindError,
)
from docflow_agent.types.boundary.api import ChatRequest, ChatResponse, ProcessRequest
from docflow_agent.usecases.chat import ChatUsecase
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases
from docflow_agent.workflow.document_workflow import (
    create_document_workflow,
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.workflow.nodes import WorkflowRuntime

router = APIRouter()


@router.post("/process")
def process(request: ProcessRequest, app_request: Request) -> dict[str, object]:
    try:
        container = app_request.app.state.container
        document_usecases = RepositoryBackedDocumentUsecases(
            artifact_repository=container.artifact_repository,
            llm_gateway=container.llm_gateway,
            processing_record_store=container.processing_record_store,
            vector_store=container.vector_store,
        )
        workflow_runtime = WorkflowRuntime(
            processing_record_store=container.processing_record_store,
            workflow_queue=container.workflow_queue,
        )
        workflow = create_document_workflow(
            usecases=document_usecases,
            artifact_repository=container.artifact_repository,
            workflow_runtime=workflow_runtime,
        )
        state = invoke_document_workflow(
            user_input=request.user_input,
            human_decisions=request.to_workflow_human_decisions(),
            workflow=workflow,
        )
    except (UnsupportedSourceKindError, UnsupportedCategoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (EcmRequestError, EcmResponseError, MailIntegrationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except LlmQuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LlmRateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
        session_id = request.session_id or str(uuid4())
        chat_usecase = ChatUsecase(
            llm_gateway=container.llm_gateway,
            chat_history_store=container.chat_history_store,
            system_prompt=get_chat_system_prompt(),
        )
        message = chat_usecase.respond(
            message=request.message,
            session_id=session_id,
        )
    except LlmQuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LlmRateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmRequestError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (UnsupportedLlmProviderError, MissingLlmApiKeyError, MissingLlmDependencyError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except DocflowError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatResponse(
        session_id=session_id,
        message=message,
        provider=container.settings.llm.provider,
        model=container.settings.llm.model,
    )
