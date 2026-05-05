from __future__ import annotations

import json
from urllib import error, request

import streamlit as st

from docflow_agent.config.prompt import get_chat_system_prompt
from docflow_agent.config.settings import get_settings
from docflow_agent.types.value.chat import ChatTurn


def main() -> None:
    st.set_page_config(page_title="docflow-agent", layout="wide")
    settings = get_settings()
    _ensure_chat_state()
    st.title("docflow-agent")

    with st.sidebar:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()
        st.caption(f"API: {settings.api.public_base_url}")
        st.caption("System prompt is configured in docflow_agent/config/prompt.py")

    _render_chat_tab(api_base_url=settings.api.public_base_url.rstrip("/"))


def _ensure_chat_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def _render_chat_tab(api_base_url: str) -> None:
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
        reply = _request_chat_reply(
            api_base_url=api_base_url,
            message=user_message,
            history=history,
        )
    except RuntimeError as exc:
        with st.chat_message("assistant"):
            st.error(str(exc))
        return

    assistant_turn = ChatTurn(role="assistant", content=reply)
    st.session_state.chat_history.append(assistant_turn)
    with st.chat_message("assistant"):
        st.markdown(reply)


def _request_chat_reply(
    api_base_url: str,
    message: str,
    history: list[ChatTurn],
) -> str:
    payload = {
        "message": message,
        "system_prompt": get_chat_system_prompt(),
        "history": [{"role": turn.role, "content": turn.content} for turn in history],
    }
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=f"{api_base_url}/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=30) as response:
            raw_response = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Chat API request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach chat API at {api_base_url}: {exc.reason}") from exc

    parsed = json.loads(raw_response)
    message_value = parsed.get("message")
    if not isinstance(message_value, str):
        raise RuntimeError("Chat API response did not include a valid message.")
    return message_value


if __name__ == "__main__":
    main()
