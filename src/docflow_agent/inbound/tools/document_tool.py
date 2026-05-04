from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from docflow_agent.inbound.langgraph.workflow import create_document_workflow

_workflow: Any = create_document_workflow()


def set_document_workflow(workflow: Any) -> None:
    global _workflow
    _workflow = workflow


@tool
def process_document_request(user_input: str) -> str:
    state = _workflow.invoke({"user_input": user_input})
    return state.get("result") or state.get("error") or "No result"
