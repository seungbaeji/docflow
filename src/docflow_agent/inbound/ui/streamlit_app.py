from __future__ import annotations

import streamlit as st

from docflow_agent.bootstrap import AppContainer, get_container
from docflow_agent.config.prompt import get_chat_system_prompt
from docflow_agent.errors import DocflowError
from docflow_agent.types.value.chat import ChatTurn


def main() -> None:
    st.set_page_config(page_title="docflow-agent", layout="wide")
    container = get_container()
    _ensure_chat_state()
    st.title("docflow-agent")

    with st.sidebar:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()
        st.caption(
            f"Provider: {container.settings.llm.provider} | Model: {container.settings.llm.model}"
        )
        st.caption("System prompt is configured in docflow_agent/config/prompt.py")

    _render_chat_tab(container)


def _ensure_chat_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


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
            system_prompt=get_chat_system_prompt(),
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


if __name__ == "__main__":
    main()
