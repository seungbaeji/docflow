from typing import TypedDict

from docflow_agent.inbound.agent.tools import process_document_tool


class AgentState(TypedDict):
    name: str
    path: str
    content_type: str
    result: dict[str, object]


def process_document_node(state: AgentState) -> AgentState:
    state["result"] = process_document_tool.invoke(
        {
            "name": state["name"],
            "path": state["path"],
            "content_type": state["content_type"],
        }
    )
    return state
