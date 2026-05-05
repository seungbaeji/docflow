from __future__ import annotations

import json
import re

from langchain_core.tools import BaseTool

from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn
from docflow_agent.types.value.document_agent import (
    DocumentAgentResult,
    DocumentAgentTrace,
    DocumentAgentToolTrace,
)


class DocumentAgentRuntime:
    def __init__(
        self,
        *,
        llm_gateway: DocumentLlmPort,
        tools: dict[str, BaseTool],
        system_prompt: str,
        max_steps: int = 4,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_steps = max_steps

    def run(self, *, prompt: str, session_id: str) -> DocumentAgentResult:
        history: list[ChatTurn] = []
        tool_traces: list[DocumentAgentToolTrace] = []
        current_message = prompt

        for _ in range(self.max_steps):
            raw_response = self.llm_gateway.chat(
                message=current_message,
                system_prompt=self._build_system_prompt(),
                history=history,
            )
            history.append(ChatTurn(role="user", content=current_message))
            history.append(ChatTurn(role="assistant", content=raw_response))
            envelope = _parse_agent_envelope(raw_response)

            envelope_type = envelope["type"]
            if envelope_type == "final_answer":
                answer = envelope["answer"]
                if not isinstance(answer, str):
                    raise DocumentAgentRuntimeError("final_answer envelope produced a non-string answer")
                return DocumentAgentResult(
                    answer=answer,
                    trace=DocumentAgentTrace(
                        prompt=prompt,
                        tool_calls=tool_traces,
                        final_answer=answer,
                    ),
                )

            tool_name = envelope["tool"]
            if not isinstance(tool_name, str):
                raise DocumentAgentRuntimeError("tool_call envelope produced a non-string tool name")
            tool = self.tools.get(tool_name)
            if tool is None:
                raise DocumentAgentRuntimeError(f"unknown tool requested: {tool_name}")
            tool_arguments = envelope["arguments"]
            if not isinstance(tool_arguments, dict):
                raise DocumentAgentRuntimeError("tool_call envelope produced non-object arguments")
            tool_result = tool.invoke(tool_arguments)
            tool_traces.append(
                DocumentAgentToolTrace(
                    tool_name=tool_name,
                    tool_input_summary=_summarize_json(tool_arguments),
                    tool_output_summary=_summarize_json(tool_result),
                )
            )
            current_message = (
                "Tool result:\n"
                f"{json.dumps({'tool': tool_name, 'result': tool_result}, ensure_ascii=False, sort_keys=True)}\n"
                "Choose the next tool or provide the final answer."
            )

        raise DocumentAgentRuntimeError("agent exceeded the maximum number of tool-calling steps")

    def _build_system_prompt(self) -> str:
        tool_lines = "\n".join(
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        )
        return f"{self.system_prompt}\n\nAvailable tools:\n{tool_lines}"


def _parse_agent_envelope(raw_response: str) -> dict[str, object]:
    payload = _extract_json_object(raw_response)
    envelope_type = payload.get("type")
    if envelope_type == "final_answer":
        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise DocumentAgentRuntimeError("final_answer envelope requires a non-empty answer")
        return {"type": "final_answer", "answer": answer}
    if envelope_type == "tool_call":
        tool_name = payload.get("tool")
        arguments = payload.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise DocumentAgentRuntimeError("tool_call envelope requires a tool name")
        if not isinstance(arguments, dict):
            raise DocumentAgentRuntimeError("tool_call envelope arguments must be an object")
        return {"type": "tool_call", "tool": tool_name, "arguments": arguments}
    raise DocumentAgentRuntimeError("agent response must be a tool_call or final_answer envelope")


def _extract_json_object(raw_response: str) -> dict[str, object]:
    stripped = raw_response.strip()
    candidate = _strip_code_fence(stripped)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match is None:
            raise DocumentAgentRuntimeError("agent response did not contain a JSON object") from None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise DocumentAgentRuntimeError("agent response contained invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DocumentAgentRuntimeError("agent response JSON must be an object")
    return payload


def _strip_code_fence(value: str) -> str:
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return value


def _summarize_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)[:800]
