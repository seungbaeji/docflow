from langgraph.graph.state import CompiledStateGraph
from langgraph.graph import END, START, StateGraph

from docflow_agent.inbound.agent.nodes import AgentState, process_source_node


def build_graph() -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    graph: StateGraph[AgentState, None, AgentState, AgentState] = StateGraph(AgentState)
    graph.add_node("process_source", process_source_node)
    graph.add_edge(START, "process_source")
    graph.add_edge("process_source", END)
    return graph.compile()
