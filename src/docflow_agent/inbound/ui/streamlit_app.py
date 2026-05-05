from __future__ import annotations

import streamlit as st

from docflow_agent.bootstrap import AppContainer, get_container
from docflow_agent.errors import DocflowError
from docflow_agent.types.value.chat import ChatTurn
from docflow_agent.workflow.document_workflow import (
    invoke_document_workflow,
    workflow_state_to_response,
)
from docflow_agent.workflow.state import HumanDecision


def main() -> None:
    st.set_page_config(page_title="docflow-agent", layout="wide")
    container = get_container()
    _ensure_chat_state()
    st.title("docflow-agent")

    with st.sidebar:
        st.subheader("Chat Settings")
        st.session_state.chat_system_prompt = st.text_area(
            "System prompt",
            value=st.session_state.chat_system_prompt,
            help="Optional system instruction applied to every chat turn.",
        )
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()
        st.caption(
            f"Provider: {container.settings.llm.provider} | Model: {container.settings.llm.model}"
        )

    chat_tab, workflow_tab = st.tabs(["Chat", "Workflow"])

    with chat_tab:
        _render_chat_tab(container)

    with workflow_tab:
        _render_workflow_tab(container)


def _ensure_chat_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_system_prompt" not in st.session_state:
        st.session_state.chat_system_prompt = ""


def _render_chat_tab(container: AppContainer) -> None:
    st.subheader("Multi-turn Chat")
    st.caption("This chat keeps local conversation history in Streamlit session state.")

    for turn in st.session_state.chat_history:
        with st.chat_message(turn.role):
            st.markdown(turn.content)

    user_message = st.chat_input("Ask something about your document workflow or data.")
    if user_message is None:
        return

    history: list[ChatTurn] = list(st.session_state.chat_history)
    st.session_state.chat_history.append(ChatTurn(role="user", content=user_message))

    with st.chat_message("user"):
        st.markdown(user_message)

    try:
        reply = container.chat_usecase.respond(
            message=user_message,
            system_prompt=st.session_state.chat_system_prompt or None,
            history=history,
        )
    except DocflowError as exc:
        with st.chat_message("assistant"):
            st.error(str(exc))
        return

    assistant_turn = ChatTurn(role="assistant", content=reply)
    st.session_state.chat_history.append(assistant_turn)
    with st.chat_message("assistant"):
        st.markdown(reply)


def _render_workflow_tab(container: AppContainer) -> None:
    st.subheader("Workflow Demo")
    user_input = st.text_area(
        "Prompt",
        value="엑셀 문서를 분석해줘",
        help="Describe the document task you want the workflow to run.",
    )
    approval = st.selectbox(
        "Mail approval decision",
        options=["none", "approve", "reject"],
        help="Inject a human decision when testing the mail approval branch.",
    )

    if not st.button("Run workflow"):
        return

    try:
        human_decisions: list[HumanDecision] | None = None
        if approval != "none":
            human_decisions = [
                {
                    "decision_id": "approve_send_mail",
                    "kind": "approve",
                    "message": "Approve sending the generated mail draft?",
                    "options": ["approve", "reject"],
                    "selected": approval,
                    "payload": None,
                }
            ]
        state = invoke_document_workflow(
            user_input=user_input,
            human_decisions=human_decisions,
            workflow=container.document_workflow,
        )
    except DocflowError as exc:
        st.error(str(exc))
        return

    st.json(workflow_state_to_response(state))


if __name__ == "__main__":
    main()
