from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "src" / "docflow_agent"


def _python_files() -> list[Path]:
    return [path for path in ROOT.rglob("*.py") if "__pycache__" not in path.parts]


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def _is_under(path: Path, *parts: str) -> bool:
    return path.is_relative_to(ROOT.joinpath(*parts))


def test_types_do_not_import_other_layers() -> None:
    forbidden_prefixes = (
        "docflow_agent.workflow",
        "docflow_agent.usecases",
        "docflow_agent.inbound",
        "docflow_agent.outbound",
        "docflow_agent.bootstrap",
    )
    for path in _python_files():
        if not _is_under(path, "types"):
            continue
        imported = _imported_modules(path)
        assert not any(module.startswith(forbidden_prefixes) for module in imported), path


def test_workflow_does_not_import_bootstrap() -> None:
    for path in _python_files():
        if not _is_under(path, "workflow"):
            continue
        imported = _imported_modules(path)
        assert "docflow_agent.bootstrap" not in imported, path


def test_inbound_does_not_import_workflow_directly() -> None:
    for path in _python_files():
        if not _is_under(path, "inbound"):
            continue
        imported = _imported_modules(path)
        assert not any(module.startswith("docflow_agent.workflow") for module in imported), path


def test_core_does_not_import_outbound_or_usecases() -> None:
    for path in _python_files():
        if not _is_under(path, "core"):
            continue
        imported = _imported_modules(path)
        assert not any(module.startswith("docflow_agent.outbound") for module in imported), path
        assert not any(module.startswith("docflow_agent.usecases") for module in imported), path


def test_outbound_does_not_import_core() -> None:
    for path in _python_files():
        if not _is_under(path, "outbound"):
            continue
        imported = _imported_modules(path)
        assert not any(module.startswith("docflow_agent.core") for module in imported), path


def test_workflow_same_level_direction_rules() -> None:
    for path in _python_files():
        imported = _imported_modules(path)
        if _is_under(path, "workflow", "agent"):
            assert not any(module.startswith("docflow_agent.workflow.chat") for module in imported), path
            assert not any(module.startswith("docflow_agent.workflow.process") for module in imported), path
        if _is_under(path, "workflow", "process"):
            assert not any(module.startswith("docflow_agent.workflow.chat") for module in imported), path
        if _is_under(path, "workflow", "document"):
            assert not any(module.startswith("docflow_agent.usecases.process_request") for module in imported), path
            assert not any(module.startswith("docflow_agent.usecases.respond_to_chat") for module in imported), path
            assert not any(module.startswith("docflow_agent.usecases.stage_upload") for module in imported), path
            if path.name != "support.py":
                document_internal_imports = [
                    module
                    for module in imported
                    if module.startswith("docflow_agent.workflow.document")
                    and module != "docflow_agent.workflow.document.support"
                ]
                assert not document_internal_imports, path
