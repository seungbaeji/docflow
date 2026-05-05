import base64
from pathlib import Path
from collections.abc import Mapping
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from docflow_agent.config.prompt import (
    get_chat_system_prompt,
    get_document_agent_system_prompt,
)
from docflow_agent.errors import (
    DocflowError,
    DocumentAgentRuntimeError,
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
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.api import (
    ChatRequest,
    ChatResponse,
    ProcessRequest,
    UploadResponse,
)
from docflow_agent.usecases.chat import ChatUsecase
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases
from docflow_agent.workflow.document_workflow import (
    create_document_workflow,
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.workflow.document_agent import DocumentAgentRuntime
from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.workflow.tools import build_document_agent_tools

router = APIRouter()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


def _requires_document_processing(message: str) -> bool:
    return _contains_any(
        message,
        (
            "분석",
            "읽어",
            "읽고",
            "해당 문서",
            "이 문서",
            "pdf",
            "문서",
            "analyze",
            "read",
            "document",
        ),
    )


def _requires_document_question(message: str) -> bool:
    return _contains_any(
        message,
        (
            "전체",
            "내용",
            "상세",
            "자세히",
            "무슨",
            "무엇",
            "금액",
            "이름",
            "요약",
            "설명",
            "해당 문서",
            "이 문서",
            "full",
            "detail",
            "content",
            "summary",
            "question",
        ),
    )


def _requires_document_agent(message: str) -> bool:
    return _requires_document_processing(message) or _requires_document_question(message)


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
        document_usecases = RepositoryBackedDocumentUsecases(
            artifact_repository=container.artifact_repository,
            llm_gateway=container.llm_gateway,
            workflow_run_store=container.workflow_run_store,
            vector_store=container.vector_store,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        )
        workflow_runtime = WorkflowRuntime(
            workflow_run_store=container.workflow_run_store,
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
    session_id = app_request.headers.get("X-Session-Id") or str(uuid4())
    file_name = _sanitize_upload_name(_decode_upload_name(app_request.headers))
    content_type = app_request.headers.get("Content-Type", "application/octet-stream")
    upload_dir = Path(container.settings.app.upload_dir).expanduser()
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4()}-{file_name}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw_file)

    document_usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=container.artifact_repository,
        llm_gateway=container.llm_gateway,
        workflow_run_store=container.workflow_run_store,
        vector_store=container.vector_store,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )
    source_ref_id = document_usecases.register_uploaded_source(
        file_info=FileInfo(
            name=file_name,
            path=str(stored_path.resolve()),
            content_type=content_type,
        )
    )
    container.session_document_store.set_current_source_ref(session_id, source_ref_id)

    return UploadResponse(
        session_id=session_id,
        file_name=file_name,
        source_ref_id=source_ref_id,
        stored_path=str(stored_path.resolve()),
        content_type=content_type,
        size_bytes=len(raw_file),
    )


@router.post("/chat")
def chat(request: ChatRequest, app_request: Request) -> ChatResponse:
    try:
        container = app_request.app.state.container
        session_id = request.session_id or str(uuid4())
        current_source_ref = container.session_document_store.get_current_source_ref(session_id)
        document_usecases = RepositoryBackedDocumentUsecases(
            artifact_repository=container.artifact_repository,
            llm_gateway=container.llm_gateway,
            workflow_run_store=container.workflow_run_store,
            vector_store=container.vector_store,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        )

        if current_source_ref is not None and _requires_document_agent(request.message):
            document_agent_runtime = DocumentAgentRuntime(
                llm_gateway=container.llm_gateway,
                tools=build_document_agent_tools(
                    session_document_store=container.session_document_store,
                    document_usecases=document_usecases,
                ),
                system_prompt=get_document_agent_system_prompt(),
            )
            try:
                message = document_agent_runtime.run(
                    prompt=request.message,
                    session_id=session_id,
                ).answer
            except DocumentAgentRuntimeError:
                if _requires_document_processing(request.message):
                    message = document_usecases.summarize_source_ref(current_source_ref)
                else:
                    message = document_usecases.answer_question_about_source_ref(
                        current_source_ref,
                        request.message,
                    )
        else:
            document_context = None
            if current_source_ref is not None:
                document_context = document_usecases.build_document_context(current_source_ref)
            chat_usecase = ChatUsecase(
                llm_gateway=container.llm_gateway,
                chat_history_store=container.chat_history_store,
                system_prompt=get_chat_system_prompt(),
            )
            message = chat_usecase.respond(
                message=request.message,
                session_id=session_id,
                document_context=document_context,
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
