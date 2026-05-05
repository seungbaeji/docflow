from __future__ import annotations

from docflow_agent.bootstrap import AppContainer
from docflow_agent.config.prompt import get_document_agent_system_prompt
from docflow_agent.tools import DOCUMENT_AGENT_TOOLS, DocumentAgentToolContext
from docflow_agent.types.value.document import DocumentPayload
from docflow_agent.workflow.agent import AgentRuntime
from docflow_agent.workflow.chat.graph import build_workflow, invoke_workflow
from docflow_agent.workflow.document import chat as document_chat
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source


def create_prep_workflow(container: AppContainer) -> object:
    return build_workflow(
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


def prepare_context(
    container: AppContainer,
    *,
    session_id: str,
    message: str,
) -> DocumentAgentToolContext:
    prep_workflow = create_prep_workflow(container)
    prep_state = invoke_workflow(
        workflow=prep_workflow,
        session_id=session_id,
        message=message,
    )
    source_ref_id = prep_state["source_ref_id"]
    payload = build_payload(container, source_ref_id)
    summary = summarize_ref(container, source_ref_id)
    return DocumentAgentToolContext(
        source_ref_id=source_ref_id,
        document_payload=payload,
        document_summary=summary,
    )


def build_runtime(
    container: AppContainer,
    *,
    tool_context: DocumentAgentToolContext,
) -> AgentRuntime:
    return AgentRuntime(
        llm_gateway=container.llm_gateway,
        tools=DOCUMENT_AGENT_TOOLS,
        tool_context=tool_context,
        runtime_store=container.runtime_store,
        system_prompt=get_document_agent_system_prompt(),
    )


def build_payload(container: AppContainer, source_ref_id: str) -> DocumentPayload:
    return document_chat.build_payload(
        container.artifact_repository,
        source_ref_id=source_ref_id,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )


def summarize_ref(container: AppContainer, source_ref_id: str) -> str:
    return document_chat.summarize_ref(
        container.artifact_repository,
        source_ref_id=source_ref_id,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )


def answer_question_about_ref(
    container: AppContainer,
    *,
    source_ref_id: str,
    question: str,
) -> str:
    return document_chat.answer_question_about_ref(
        container.artifact_repository,
        source_ref_id=source_ref_id,
        question=question,
        llm_gateway=container.llm_gateway,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )


def build_context_by_ref(container: AppContainer, source_ref_id: str) -> str:
    return document_chat.build_context_by_ref(
        container.artifact_repository,
        source_ref_id=source_ref_id,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )
