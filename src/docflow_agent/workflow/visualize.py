from __future__ import annotations

from pathlib import Path
from typing import Any

from docflow_agent.bootstrap import build_container
from docflow_agent.workflow.document import mail as document_mail
from docflow_agent.workflow.document import parse as document_parse
from docflow_agent.workflow.document import source as document_source
from docflow_agent.workflow.document_workflow import create_document_workflow
from docflow_agent.workflow.nodes import WorkflowRuntime


def build_document_workflow_graph() -> Any:
    container = build_container()
    workflow_runtime = WorkflowRuntime(
        workflow_run_store=container.workflow_run_store,
        workflow_queue=container.workflow_queue,
    )
    workflow = create_document_workflow(
        artifact_repository=container.artifact_repository,
        workflow_runtime=workflow_runtime,
        load_source=lambda user_input: document_source.load_source(
            container.artifact_repository,
            user_input=user_input,
        ),
        parse_units=lambda source_ref_id: document_parse.parse_units(
            container.artifact_repository,
            source_ref_id=source_ref_id,
            pdf_client=container.pdf_client,
            pdf_parser=container.pdf_parser,
        ),
        categorize_units=lambda unit_ref_ids: document_parse.categorize_units(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        combine_bundle=lambda unit_ref_ids: document_parse.combine_bundle(
            container.artifact_repository,
            unit_ref_ids=unit_ref_ids,
        ),
        analyze=lambda bundle_ref_id: document_mail.analyze(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
            workflow_run_store=container.workflow_run_store,
            vector_store=container.vector_store,
        ),
        filter_dataset=lambda bundle_ref_id: document_mail.filter_dataset(
            container.artifact_repository,
            bundle_ref_id=bundle_ref_id,
        ),
        compose_mail=lambda dataset_ref_id: document_mail.compose_mail(
            container.artifact_repository,
            dataset_ref_id=dataset_ref_id,
            llm_gateway=container.llm_gateway,
        ),
        send_mail=lambda draft_ref_id: document_mail.send_mail(
            container.artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=container.workflow_run_store,
        ),
        reject_send_mail=lambda draft_ref_id: document_mail.reject_send_mail(
            container.artifact_repository,
            draft_ref_id=draft_ref_id,
            workflow_run_store=container.workflow_run_store,
        ),
        handle_unknown=lambda user_input: document_mail.handle_unknown(
            container.artifact_repository,
            user_input=user_input,
            workflow_run_store=container.workflow_run_store,
        ),
    )
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
