from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json

from langchain.tools import BaseTool, ToolRuntime
from langgraph.store.base import BaseStore

from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.types.value.document_agent import DocumentAgentToolContext


def invoke_tool(
    *,
    tools_by_name: dict[str, BaseTool],
    tool_context: DocumentAgentToolContext,
    runtime_store: BaseStore | None,
    tool_name: str,
    tool_arguments: dict[str, object],
) -> object:
    tool = tools_by_name.get(tool_name)
    if tool is None:
        raise DocumentAgentRuntimeError(f"unknown tool requested: {tool_name}")

    tool_runtime: ToolRuntime[DocumentAgentToolContext, dict[str, list[object]]] = ToolRuntime(
        state={"messages": []},
        context=tool_context,
        config={},
        stream_writer=lambda _value: None,
        tool_call_id=f"tool-call-{tool_name}",
        store=runtime_store,
    )
    invoke_payload = dict(tool_arguments)
    invoke_payload["runtime"] = tool_runtime
    return tool.invoke(invoke_payload)


def serialize_tool_result(value: object) -> dict[str, object]:
    if is_dataclass(value):
        serialized = asdict(value)  # type: ignore[arg-type]
        if isinstance(serialized, dict):
            return serialized
    if isinstance(value, dict):
        return value
    raise DocumentAgentRuntimeError("tool result must be a dataclass value object or a dict")


def summarize_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)[:800]
