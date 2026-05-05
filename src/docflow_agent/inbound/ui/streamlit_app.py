from __future__ import annotations

import base64
import json
import mimetypes
from typing import Any
from uuid import uuid4
from urllib import error, request

import streamlit as st

from docflow_agent.config.settings import get_settings
from docflow_agent.types.value.chat import ChatTurn


def main() -> None:
    st.set_page_config(page_title="docflow-agent", layout="wide")
    settings = get_settings()
    _ensure_chat_state()
    st.title("docflow-agent")

    with st.sidebar:
        uploaded_file = st.file_uploader(
            "Upload document",
            type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg", "eml"],
        )
        if uploaded_file is not None:
            _handle_uploaded_file(
                api_base_url=settings.api.public_base_url.rstrip("/"),
                uploaded_file=uploaded_file,
            )
        _render_uploaded_document_panel(api_base_url=settings.api.public_base_url.rstrip("/"))

        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.session_state.chat_session_id = str(uuid4())
            st.rerun()
        st.caption(f"API: {settings.api.public_base_url}")
        st.caption(f"Session: {st.session_state.chat_session_id}")

    _render_chat_view(api_base_url=settings.api.public_base_url.rstrip("/"))


def _ensure_chat_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid4())
    if "uploaded_document" not in st.session_state:
        st.session_state.uploaded_document = None
    if "uploaded_document_key" not in st.session_state:
        st.session_state.uploaded_document_key = None
    if "last_workflow_response" not in st.session_state:
        st.session_state.last_workflow_response = None


def _render_chat_view(api_base_url: str) -> None:
    st.subheader("Multi-turn Chat")
    st.caption("This chat keeps local conversation history in Streamlit session state.")

    if st.session_state.uploaded_document is not None:
        uploaded_document = st.session_state.uploaded_document
        st.info(
            "Uploaded document available: "
            f"{uploaded_document['file_name']} -> {uploaded_document['stored_path']}"
        )

    if st.session_state.last_workflow_response is not None:
        workflow_response = st.session_state.last_workflow_response
        st.success(
            f"Workflow result: {workflow_response.get('result', 'No result')} "
            f"(flow={workflow_response.get('flow')}, step={workflow_response.get('current_step')})"
        )

    for turn in st.session_state.chat_history:
        with st.chat_message(turn.role):
            st.markdown(turn.content)

    user_message = st.chat_input("Ask something about your document workflow or data.")
    if user_message is None:
        return

    st.session_state.chat_history.append(ChatTurn(role="user", content=user_message))

    with st.chat_message("user"):
        st.markdown(user_message)

    try:
        reply = _request_chat_reply(
            api_base_url=api_base_url,
            message=user_message,
            session_id=st.session_state.chat_session_id,
        )
    except RuntimeError as exc:
        with st.chat_message("assistant"):
            st.error(str(exc))
        return

    assistant_turn = ChatTurn(role="assistant", content=reply)
    st.session_state.chat_history.append(assistant_turn)
    with st.chat_message("assistant"):
        st.markdown(reply)


def _handle_uploaded_file(api_base_url: str, uploaded_file: Any) -> None:
    upload_key = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.uploaded_document_key == upload_key:
        return

    try:
        upload_response = _upload_document(
            api_base_url=api_base_url,
            session_id=st.session_state.chat_session_id,
            file_name=uploaded_file.name,
            content_type=uploaded_file.type or _guess_content_type(uploaded_file.name),
            payload=uploaded_file.getvalue(),
        )
    except RuntimeError as exc:
        st.sidebar.error(str(exc))
        return

    st.session_state.uploaded_document = upload_response
    if isinstance(upload_response.get("session_id"), str):
        st.session_state.chat_session_id = upload_response["session_id"]
    st.session_state.uploaded_document_key = upload_key
    st.session_state.last_workflow_response = None
    st.sidebar.success(f"Uploaded {upload_response['file_name']}")


def _render_uploaded_document_panel(api_base_url: str) -> None:
    uploaded_document = st.session_state.uploaded_document
    if uploaded_document is None:
        return

    st.caption(f"Stored: {uploaded_document['stored_path']}")
    st.caption(f"Type: {uploaded_document['content_type']}")
    st.caption(f"Size: {uploaded_document['size_bytes']} bytes")

    if st.button("Analyze uploaded file"):
        prompt = _build_analysis_prompt(uploaded_document["stored_path"], uploaded_document["content_type"])
        try:
            st.session_state.last_workflow_response = _request_workflow_process(
                api_base_url=api_base_url,
                user_input=prompt,
            )
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.rerun()

    if st.button("Clear uploaded file"):
        st.session_state.uploaded_document = None
        st.session_state.uploaded_document_key = None
        st.session_state.last_workflow_response = None
        st.rerun()


def _build_analysis_prompt(stored_path: str, content_type: str) -> str:
    if content_type == "application/pdf":
        return f"이 PDF 파일을 분석해줘 {stored_path}"
    return f"이 문서를 분석해줘 {stored_path}"


def _request_chat_reply(
    api_base_url: str,
    message: str,
    session_id: str,
) -> str:
    payload = {
        "message": message,
        "session_id": session_id,
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
    response_session_id = parsed.get("session_id")
    message_value = parsed.get("message")
    if isinstance(response_session_id, str):
        st.session_state.chat_session_id = response_session_id
    if not isinstance(message_value, str):
        raise RuntimeError("Chat API response did not include a valid message.")
    return message_value


def _request_workflow_process(
    api_base_url: str,
    user_input: str,
) -> dict[str, object]:
    payload = {"user_input": user_input}
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=f"{api_base_url}/process",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=60) as response:
            raw_response = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Workflow API request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach workflow API at {api_base_url}: {exc.reason}") from exc

    parsed = json.loads(raw_response)
    if not isinstance(parsed, dict):
        raise RuntimeError("Workflow API response did not return an object.")
    return parsed


def _upload_document(
    api_base_url: str,
    *,
    session_id: str,
    file_name: str,
    content_type: str,
    payload: bytes,
) -> dict[str, object]:
    encoded_file_name = base64.urlsafe_b64encode(file_name.encode("utf-8")).decode("ascii")
    http_request = request.Request(
        url=f"{api_base_url}/uploads",
        data=payload,
        headers={
            "Content-Type": content_type,
            "X-Filename-Base64": encoded_file_name,
            "X-Session-Id": session_id,
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=60) as response:
            raw_response = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Upload API request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach upload API at {api_base_url}: {exc.reason}") from exc

    parsed = json.loads(raw_response)
    if not isinstance(parsed, dict):
        raise RuntimeError("Upload API response did not return an object.")
    return parsed


def _guess_content_type(file_name: str) -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


if __name__ == "__main__":
    main()
