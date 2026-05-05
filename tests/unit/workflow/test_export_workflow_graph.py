from pathlib import Path

from docflow_agent.bootstrap import build_container
from docflow_agent.workflow.process.factory import create_workflow
from docflow_agent.workflow.visualize import export_document_workflow_graph


def test_export_document_workflow_graph_writes_mermaid(tmp_path: Path) -> None:
    output_path = tmp_path / "document_workflow_graph.mmd"
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

    exported_path = export_document_workflow_graph(
        graph=workflow.get_graph(),
        output_path=output_path,
        format="mermaid",
    )

    assert exported_path == output_path
    content = output_path.read_text(encoding="utf-8")
    assert "graph TD" in content
    assert "select_flow" in content
    assert "request_send_mail_approval" in content


def test_export_document_workflow_graph_writes_ascii(tmp_path: Path) -> None:
    output_path = tmp_path / "document_workflow_graph.txt"
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

    exported_path = export_document_workflow_graph(
        graph=workflow.get_graph(),
        output_path=output_path,
        format="ascii",
    )

    assert exported_path == output_path
    content = output_path.read_text(encoding="utf-8")
    assert "select_flow" in content
    assert "compose_mail" in content
