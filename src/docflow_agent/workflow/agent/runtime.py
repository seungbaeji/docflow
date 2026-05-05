"""Agent runtime for prompt-started tool-calling.

The runtime drives the conversation loop between the LLM and internal tools.
It does not select the current document itself; it consumes prepared tool
context supplied by the workflow layer.
"""

from __future__ import annotations

import json

from langchain.tools import BaseTool
from langgraph.store.base import BaseStore

from docflow_agent.errors import DocumentAgentRuntimeError
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn
from docflow_agent.types.value.document_agent import (
    DocumentAgentResult,
    DocumentAgentToolContext,
    DocumentAgentToolTrace,
    DocumentAgentTrace,
)
from docflow_agent.workflow.agent.envelope import parse_envelope
from docflow_agent.workflow.agent.tool_runner import invoke_tool, serialize_tool_result, summarize_json


class AgentRuntime:
    """Run a bounded tool-calling loop over prepared document context.

    The runtime expects workflow to provide a fully prepared tool context
    ahead of time. Its job is only to alternate between LLM envelopes and
    tool execution until a final answer is produced or the step budget ends.
    """

    def __init__(
        self,
        *,
        llm_gateway: DocumentLlmPort,
        tools: list[BaseTool] | tuple[BaseTool, ...],
        tool_context: DocumentAgentToolContext,
        runtime_store: BaseStore | None,
        system_prompt: str,
        max_steps: int = 4,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.tools = list(tools)
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.tool_context = tool_context
        self.runtime_store = runtime_store
        self.system_prompt = system_prompt
        self.max_steps = max_steps

    def run(self, *, prompt: str) -> DocumentAgentResult:
        """Execute the agent loop until a final answer or step limit is reached.

        Returns a structured result containing both the final answer and a
        trace of tool calls, so tests and diagnostics can inspect trajectory
        without depending on UI or HTTP layers.
        """
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
            envelope = parse_envelope(raw_response)

            if envelope["type"] == "final_answer":
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
            tool_arguments = envelope["arguments"]
            if not isinstance(tool_arguments, dict):
                raise DocumentAgentRuntimeError("tool_call envelope produced non-object arguments")

            tool_result = invoke_tool(
                tools_by_name=self.tools_by_name,
                tool_context=self.tool_context,
                runtime_store=self.runtime_store,
                tool_name=tool_name,
                tool_arguments=tool_arguments,
            )
            serialized_tool_result = serialize_tool_result(tool_result)
            tool_traces.append(
                DocumentAgentToolTrace(
                    tool_name=tool_name,
                    tool_input_summary=summarize_json(tool_arguments),
                    tool_output_summary=summarize_json(serialized_tool_result),
                )
            )
            current_message = (
                "Tool result:\n"
                f"{json.dumps({'tool': tool_name, 'result': serialized_tool_result}, ensure_ascii=False, sort_keys=True)}\n"
                "Choose the next tool or provide the final answer."
            )

        raise DocumentAgentRuntimeError("agent exceeded the maximum number of tool-calling steps")

    def _build_system_prompt(self) -> str:
        """Append available tool descriptions to the configured system prompt.

        This keeps tool discovery inside the runtime so callers only need to
        supply the base system prompt and tool list.
        """
        tool_lines = "\n".join(f"- {tool.name}: {tool.description}" for tool in self.tools)
        return f"{self.system_prompt}\n\nAvailable tools:\n{tool_lines}"
