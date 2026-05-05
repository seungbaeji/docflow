from __future__ import annotations

from pathlib import Path
from typing import Any

from docflow_agent.bootstrap import build_container
from docflow_agent.workflow.process.factory import create_workflow


def build_document_workflow_graph() -> Any:
    container = build_container()
    workflow = create_workflow(container)
    return workflow.get_graph()


def export_document_workflow_graph(
    *,
    output_path: Path,
    format: str,
) -> Path:
    graph = build_document_workflow_graph()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "mermaid":
        output_path.write_text(graph.draw_mermaid(), encoding="utf-8")
        return output_path
    if format == "ascii":
        try:
            ascii_graph = graph.draw_ascii()
        except ImportError:
            ascii_graph = _draw_ascii_fallback(graph)
        output_path.write_text(ascii_graph, encoding="utf-8")
        return output_path
    if format == "png":
        png_bytes = graph.draw_mermaid_png(output_file_path=str(output_path))
        if not output_path.exists():
            output_path.write_bytes(png_bytes)
        return output_path
    raise ValueError(f"Unsupported graph export format: {format}")


def _draw_ascii_fallback(graph: Any) -> str:
    nodes = sorted(node.id for node in graph.nodes.values())
    edges = sorted(
        f"{edge.source} -> {edge.target}" + (" [conditional]" if edge.conditional else "")
        for edge in graph.edges
    )
    return "\n".join(
        [
            "Document Workflow Graph",
            "",
            "Nodes:",
            *[f"- {node}" for node in nodes],
            "",
            "Edges:",
            *[f"- {edge}" for edge in edges],
        ]
    )
