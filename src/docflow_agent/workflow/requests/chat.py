from __future__ import annotations

from docflow_agent.bootstrap import AppContainer
from docflow_agent.config.prompt import (
    get_chat_system_prompt,
    get_document_agent_system_prompt,
)
from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.tools import DOCUMENT_AGENT_TOOLS, DocumentAgentToolContext
from docflow_agent.usecases.chat import respond_in_chat
from docflow_agent.workflow.document import chat as document_chat
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source
from docflow_agent.workflow.document_agent import DocumentAgentRuntime
from docflow_agent.workflow.document_chat_workflow import (
    build_document_chat_workflow,
    invoke_document_chat_workflow,
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
        prep_workflow = build_document_chat_workflow(
            artifact_repository=container.artifact_repository,
            session_document_store=container.session_document_store,
            source_from_upload=lambda upload_id: document_source.source_from_upload(
                container.artifact_repository,
                upload_id=upload_id,
            ),
            parse_units=lambda source_ref_id: document_parse.parse_units(
                container.artifact_repository,
                source_ref_id=source_ref_id,
                pdf_client=container.pdf_client,
                pdf_parser=container.pdf_parser,
            ),
            categorize_units=lambda unit_ref_ids: document_parse.categorize_units(
                container.artifact_repository,
                unit_ref_ids=unit_ref_ids,
            ),
            combine_bundle=lambda unit_ref_ids: document_parse.combine_bundle(
                container.artifact_repository,
                unit_ref_ids=unit_ref_ids,
            ),
            analyze=lambda bundle_ref_id: document_mail.analyze(
                container.artifact_repository,
                bundle_ref_id=bundle_ref_id,
                workflow_run_store=container.workflow_run_store,
                vector_store=container.vector_store,
            ),
        )
        prep_state = invoke_document_chat_workflow(
            workflow=prep_workflow,
            session_id=session_id,
            message=message,
        )
        source_ref_id = prep_state["source_ref_id"]
        document_payload = document_chat.build_payload(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        )
        document_summary = document_chat.summarize_ref(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        )
        document_agent_runtime = DocumentAgentRuntime(
            llm_gateway=container.llm_gateway,
            tools=DOCUMENT_AGENT_TOOLS,
            tool_context=DocumentAgentToolContext(
                source_ref_id=source_ref_id,
                document_payload=document_payload,
                document_summary=document_summary,
            ),
            runtime_store=container.runtime_store,
            system_prompt=get_document_agent_system_prompt(),
        )
        try:
            return document_agent_runtime.run(prompt=message).answer
        except DocumentAgentRuntimeError:
            if _requires_document_processing(message):
                return document_summary
            return document_chat.answer_question_about_ref(
                container.artifact_repository,
                source_ref_id=source_ref_id,
                question=message,
                llm_gateway=container.llm_gateway,
                pdf_client=container.pdf_client,
                pdf_parser=container.pdf_parser,
            )

    document_context = None
    if current_source_ref is not None:
        document_context = document_chat.build_context_by_ref(
            container.artifact_repository,
            source_ref_id=current_source_ref,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        )
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
