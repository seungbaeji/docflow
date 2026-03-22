from typing import TypedDict

from docflow_agent.inbound.agent.tools import process_source_tool


class AgentState(TypedDict):
    name: str
    location: str
    content_type: str
    source_system: str
    result: dict[str, object]


def process_source_node(state: AgentState) -> AgentState:
    state["result"] = process_source_tool.invoke(
        {
            "name": state["name"],
            "location": state["location"],
            "content_type": state["content_type"],
            "source_system": state["source_system"],
        }
    )
    return state
