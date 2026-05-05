from __future__ import annotations

from docflow_agent.bootstrap import AppContainer
from docflow_agent.config.prompt import (
    get_chat_system_prompt,
)
from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.usecases.chat import respond_in_chat
from docflow_agent.workflow.chat.factory import (
    answer_question_about_ref,
    build_context_by_ref,
    build_runtime,
    prepare_context,
)


def respond_to_chat(
    *,
    container: AppContainer,
    session_id: str,
    message: str,
) -> str:
    current_source_ref = container.session_document_store.get_current_source_ref(session_id)
    current_upload_id = container.session_document_store.get_current_upload_id(session_id)

    if (current_source_ref is not None or current_upload_id is not None) and _requires_document_agent(
        message
    ):
        tool_context = prepare_context(
            container,
            session_id=session_id,
            message=message,
        )
        document_agent_runtime = build_runtime(container, tool_context=tool_context)
        try:
            return document_agent_runtime.run(prompt=message).answer
        except DocumentAgentRuntimeError:
            if _requires_document_processing(message):
                return tool_context.document_summary
            return answer_question_about_ref(
                container,
                source_ref_id=tool_context.source_ref_id,
                question=message,
            )

    document_context = None
    if current_source_ref is not None:
        document_context = build_context_by_ref(container, current_source_ref)
    return respond_in_chat(
        message=message,
        session_id=session_id,
        llm_gateway=container.llm_gateway,
        chat_history_store=container.chat_history_store,
        system_prompt=get_chat_system_prompt(),
        document_context=document_context,
    )


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
