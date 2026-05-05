#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from docflow_agent.bootstrap import build_container
from docflow_agent.workflow.process.factory import create_workflow
from docflow_agent.workflow.visualize import export_document_workflow_graph  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[1]


def _default_output_path(format: str) -> Path:
    extension = "mmd" if format == "mermaid" else format
    return REPO_ROOT / "tmp" / f"document_workflow_graph.{extension}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the current document workflow graph as mermaid, ascii, or png."
    )
    parser.add_argument(
        "--format",
        choices=["mermaid", "ascii", "png"],
        default="mermaid",
        help="Output format for the workflow graph.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path. Defaults to tmp/document_workflow_graph.<ext>.",
    )
    args = parser.parse_args()

    output_path = args.output or _default_output_path(args.format)
    container = build_container()
    workflow = create_workflow(
        artifact_repository=container.artifact_repository,
        workflow_run_store=container.workflow_run_store,
        workflow_queue=container.workflow_queue,
        vector_store=container.vector_store,
        llm_gateway=container.llm_gateway,
        pdf_client=container.pdf_client,
        pdf_parser=container.pdf_parser,
    )
    exported = export_document_workflow_graph(
        graph=workflow.get_graph(),
        output_path=output_path,
        format=args.format,
    )
    print(exported)


if __name__ == "__main__":
    main()
