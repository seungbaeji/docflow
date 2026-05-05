import base64
from pathlib import Path
from collections.abc import Callable, Mapping
from typing import TypedDict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from docflow_agent.bootstrap import AppContainer
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
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.types.value.results import UsecaseOutcome
from docflow_agent.usecases.chat import respond_in_chat
from docflow_agent.workflow.document import chat as document_chat
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source
from docflow_agent.workflow.document_chat_workflow import (
    build_document_chat_workflow,
    invoke_document_chat_workflow,
)
from docflow_agent.workflow.document_workflow import (
    create_document_workflow,
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.workflow.document_agent import DocumentAgentRuntime
from docflow_agent.workflow.nodes import WorkflowRuntime
from docflow_agent.workflow.tools import (
    bind_document_agent_tools,
    DocumentAgentToolContext,
)

router = APIRouter()


class DocumentWorkflowKwargs(TypedDict):
    load_source: Callable[[str], str]
    parse_units: Callable[[str], list[str]]
    categorize_units: Callable[[list[str]], list[str]]
    combine_bundle: Callable[[list[str]], str]
    analyze: Callable[[str], UsecaseOutcome]
    filter_dataset: Callable[[str], str]
    compose_mail: Callable[[str], str]
    send_mail: Callable[[str], UsecaseOutcome]
    reject_send_mail: Callable[[str | None], UsecaseOutcome]
    handle_unknown: Callable[[str], UsecaseOutcome]


class DocumentChatFunctions(TypedDict):
    stage_upload: Callable[[str, str, str, int], str]
    source_from_upload: Callable[[str], str]
    parse_units: Callable[[str], list[str]]
    categorize_units: Callable[[list[str]], list[str]]
    combine_bundle: Callable[[list[str]], str]
    analyze: Callable[[str], UsecaseOutcome]
    build_document_payload: Callable[[str], DocumentPayload]
    build_document_context: Callable[[str], str]
    summarize_source_ref: Callable[[str], str]
    answer_question_about_source_ref: Callable[[str, str], str]


def _document_workflow_kwargs(container: AppContainer) -> DocumentWorkflowKwargs:
    return {
        "load_source": lambda user_input: document_source.load_source(
            container.artifact_repository,
            user_input=user_input,
        ),
        "parse_units": lambda source_ref_id: document_parse.parse_units(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        "categorize_units": lambda unit_ref_ids: document_parse.categorize_units(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "combine_bundle": lambda unit_ref_ids: document_parse.combine_bundle(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "analyze": lambda bundle_ref_id: document_mail.analyze(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=container.workflow_run_store,
            vector_store=container.vector_store,
        ),
        "filter_dataset": lambda bundle_ref_id: document_mail.filter_dataset(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
        ),
        "compose_mail": lambda dataset_ref_id: document_mail.compose_mail(
            container.artifact_repository,
            dataset_ref_id=dataset_ref_id,
            llm_gateway=container.llm_gateway,
        ),
        "send_mail": lambda draft_ref_id: document_mail.send_mail(
            container.artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=container.workflow_run_store,
        ),
        "reject_send_mail": lambda draft_ref_id: document_mail.reject_send_mail(
            container.artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=container.workflow_run_store,
        ),
        "handle_unknown": lambda user_input: document_mail.handle_unknown(
            container.artifact_repository,
            user_input=user_input,
            workflow_run_store=container.workflow_run_store,
        ),
    }


def _document_chat_functions(container: AppContainer) -> DocumentChatFunctions:
    return {
        "stage_upload": lambda file_name, stored_path, content_type, size_bytes: document_source.stage_upload(
            container.artifact_repository,
            file_name=file_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=size_bytes,
        ),
        "source_from_upload": lambda upload_id: document_source.source_from_upload(
            container.artifact_repository,
            upload_id=upload_id,
        ),
        "parse_units": lambda source_ref_id: document_parse.parse_units(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        "categorize_units": lambda unit_ref_ids: document_parse.categorize_units(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "combine_bundle": lambda unit_ref_ids: document_parse.combine_bundle(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        "analyze": lambda bundle_ref_id: document_mail.analyze(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=container.workflow_run_store,
            vector_store=container.vector_store,
        ),
        "build_document_payload": lambda source_ref_id: document_chat.build_document_payload(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        "build_document_context": lambda source_ref_id: document_chat.build_document_context_by_ref(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        "summarize_source_ref": lambda source_ref_id: document_chat.summarize_source_ref(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        "answer_question_about_source_ref": lambda source_ref_id, question: document_chat.answer_question_about_source_ref(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            question=question,
            llm_gateway=container.llm_gateway,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
    }


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
        workflow_functions = _document_workflow_kwargs(container)
        workflow_runtime = WorkflowRuntime(
            workflow_run_store=container.workflow_run_store,
            workflow_queue=container.workflow_queue,
        )
        workflow = create_document_workflow(
            artifact_repository=container.artifact_repository,
            workflow_runtime=workflow_runtime,
            **workflow_functions,
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

    document_functions = _document_chat_functions(container)
    upload_id = document_functions["stage_upload"](
        file_name,
        str(stored_path.resolve()),
        content_type,
        len(raw_file),
    )
    container.session_document_store.set_current_upload_id(session_id, upload_id)
    container.session_document_store.clear_current_source_ref(session_id)

    return UploadResponse(
        session_id=session_id,
        upload_id=upload_id,
        file_name=file_name,
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
        current_upload_id = container.session_document_store.get_current_upload_id(session_id)
        document_functions = _document_chat_functions(container)

        if (current_source_ref is not None or current_upload_id is not None) and _requires_document_agent(
            request.message
        ):
            prep_workflow = build_document_chat_workflow(
                artifact_repository=container.artifact_repository,
                session_document_store=container.session_document_store,
                source_from_upload=document_functions["source_from_upload"],
                parse_units=document_functions["parse_units"],
                categorize_units=document_functions["categorize_units"],
                combine_bundle=document_functions["combine_bundle"],
                analyze=document_functions["analyze"],
            )
            prep_state = invoke_document_chat_workflow(
                workflow=prep_workflow,
                session_id=session_id,
                message=request.message,
            )
            source_ref_id = prep_state["source_ref_id"]
            document_agent_runtime = DocumentAgentRuntime(
                llm_gateway=container.llm_gateway,
                tools=bind_document_agent_tools(
                    build_document_payload=document_functions["build_document_payload"],
                    summarize_source_ref=document_functions["summarize_source_ref"],
                ),
                tool_context=DocumentAgentToolContext(
                    source_ref_id=source_ref_id,
                ),
                runtime_store=container.runtime_store,
                system_prompt=get_document_agent_system_prompt(),
            )
            try:
                message = document_agent_runtime.run(prompt=request.message).answer
            except DocumentAgentRuntimeError:
                if _requires_document_processing(request.message):
                    message = document_functions["summarize_source_ref"](source_ref_id)
                else:
                    message = document_functions["answer_question_about_source_ref"](
                        source_ref_id,
                        request.message,
                    )
        else:
            document_context = None
            if current_source_ref is not None:
                document_context = document_functions["build_document_context"](current_source_ref)
            message = respond_in_chat(
                message=request.message,
                session_id=session_id,
                llm_gateway=container.llm_gateway,
                chat_history_store=container.chat_history_store,
                system_prompt=get_chat_system_prompt(),
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
