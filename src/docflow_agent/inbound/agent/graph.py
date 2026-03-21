from langgraph.graph import END, START, StateGraph

from docflow_agent.inbound.agent.nodes import AgentState, process_document_node


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("process_document", process_document_node)
    graph.add_edge(START, "process_document")
    graph.add_edge("process_document", END)
    return graph.compile()
