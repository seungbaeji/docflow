import base64
from pathlib import Path
from collections.abc import Mapping
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

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
    PdfIntegrationError,
    UnsupportedCategoryError,
    UnsupportedLlmProviderError,
    UnsupportedSourceKindError,
)
from docflow_agent.types.boundary.api import (
    ChatRequest,
    ChatResponse,
    ProcessRequest,
    UploadResponse,
)
from docflow_agent.workflow.requests import (
    process_request,
    respond_to_chat,
    stage_upload,
)
from docflow_agent.workflow.document_workflow import workflow_state_to_response


router = APIRouter()


def _decode_upload_name(headers: Mapping[str, str]) -> str:
    if not headers:
        return ""
    encoded_name = headers.get("X-Filename-Base64")
    if isinstance(encoded_name, str) and encoded_name:
        try:
            return base64.urlsafe_b64decode(encoded_name.encode("ascii")).decode("utf-8")
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Upload filename header is invalid.") from exc
    plain_name = headers.get("X-Filename")
    return plain_name if isinstance(plain_name, str) else ""


def _sanitize_upload_name(file_name: str) -> str:
    safe_name = Path(file_name).name.strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Upload filename is required.")
    return safe_name


@router.post("/process")
def process(request: ProcessRequest, app_request: Request) -> dict[str, object]:
    try:
        container = app_request.app.state.container
        state = process_request(
            container=container,
            user_input=request.user_input,
            human_decisions=request.to_workflow_human_decisions(),
        )
    except (UnsupportedSourceKindError, UnsupportedCategoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PdfIntegrationError as exc:
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


@router.post("/uploads")
async def upload_document(app_request: Request) -> UploadResponse:
    raw_file = await app_request.body()
    if not raw_file:
        raise HTTPException(status_code=400, detail="Upload body must not be empty.")

    container = app_request.app.state.container
    return stage_upload(
        container=container,
        session_id=app_request.headers.get("X-Session-Id"),
        file_name=_sanitize_upload_name(_decode_upload_name(app_request.headers)),
        content_type=app_request.headers.get("Content-Type", "application/octet-stream"),
        raw_file=raw_file,
    )


@router.post("/chat")
def chat(request: ChatRequest, app_request: Request) -> ChatResponse:
    try:
        container = app_request.app.state.container
        session_id = request.session_id or str(uuid4())
        message = respond_to_chat(
            container=container,
            session_id=session_id,
            message=request.message,
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
