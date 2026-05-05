from __future__ import annotations

import json
import re

from docflow_agent.errors import DocumentAgentRuntimeError


def parse_envelope(raw_response: str) -> dict[str, object]:
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
