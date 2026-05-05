from __future__ import annotations

import json
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from docflow_agent.errors import EmptyPdfOutputError, MissingPdfDependencyError, PdfIntegrationError
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument, PdfElement


class OpenDataLoaderPdfClient:
    def __init__(
        self,
        *,
        format: str = "markdown,json",
        hybrid: str | None = None,
        use_struct_tree: bool = True,
        quiet: bool = True,
        keep_line_breaks: bool = False,
    ) -> None:
        self.format = format
        self.hybrid = hybrid
        self.use_struct_tree = use_struct_tree
        self.quiet = quiet
        self.keep_line_breaks = keep_line_breaks


def extract_pdf_document(
    client: OpenDataLoaderPdfClient,
    file_info: FileInfo,
) -> PdfDocument:
    if file_info.content_type != "application/pdf":
        raise PdfIntegrationError(file_info.name, "content_type must be application/pdf")

    opendataloader_pdf = _import_opendataloader_pdf()
    source_path = Path(file_info.path)
    if not source_path.exists():
        raise PdfIntegrationError(file_info.name, "source file does not exist")

    with TemporaryDirectory(prefix="docflow-pdf-") as output_dir:
        try:
            convert_kwargs: dict[str, Any] = {
                "input_path": [str(source_path)],
                "output_dir": output_dir,
                "format": client.format,
                "use_struct_tree": client.use_struct_tree,
                "quiet": client.quiet,
                "keep_line_breaks": client.keep_line_breaks,
            }
            if client.hybrid is not None:
                convert_kwargs["hybrid"] = client.hybrid

            # Official docs recommend batching files because each convert() call spawns a JVM.
            opendataloader_pdf.convert(**convert_kwargs)
        except Exception as exc:  # pragma: no cover - third-party error shape is not stable
            raise PdfIntegrationError(file_info.name, str(exc)) from exc

        return _load_pdf_outputs(file_info=file_info, output_dir=Path(output_dir))


def _import_opendataloader_pdf() -> Any:
    try:
        return importlib.import_module("opendataloader_pdf")
    except ImportError as exc:  # pragma: no cover - exercised by integration test
        raise MissingPdfDependencyError("opendataloader-pdf") from exc


def _load_pdf_outputs(file_info: FileInfo, output_dir: Path) -> PdfDocument:
    stem = Path(file_info.name).stem
    markdown = _read_optional_text(output_dir / f"{stem}.md")
    html = _read_optional_text(output_dir / f"{stem}.html")
    text = _read_optional_text(output_dir / f"{stem}.txt")
    raw_json = _read_optional_json(output_dir / f"{stem}.json")

    if markdown is None and html is None and text is None and not raw_json:
        raise EmptyPdfOutputError(file_info.name)

    metadata = {
        key: raw_json.get(key)
        for key in ("author", "title", "creation date", "modification date")
        if raw_json.get(key) is not None
    }

    return PdfDocument(
        file_name=str(raw_json.get("file name") or file_info.name),
        page_count=int(raw_json.get("number of pages") or 0),
        markdown=markdown,
        html=html,
        text=text,
        elements=_flatten_elements(raw_json.get("kids", [])),
        metadata=metadata,
        raw_json=raw_json,
    )


def _read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise PdfIntegrationError(path.name, "JSON output root must be an object")
    return loaded


def _flatten_elements(nodes: object) -> list[PdfElement]:
    if not isinstance(nodes, list):
        return []

    flattened: list[PdfElement] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue

        flattened.append(
            PdfElement(
                element_type=str(node.get("type") or "unknown"),
                page_number=_coerce_page_number(node.get("page number")),
                content=_coerce_content(node),
                bounding_box=_coerce_bounding_box(node.get("bounding box")),
                metadata={
                    key: value
                    for key, value in node.items()
                    if key
                    not in {
                        "type",
                        "page number",
                        "content",
                        "text",
                        "bounding box",
                        "kids",
                    }
                },
            )
        )
        flattened.extend(_flatten_elements(node.get("kids", [])))
    return flattened


def _coerce_page_number(value: object) -> int | None:
    if isinstance(value, int) and value >= 1:
        return value
    return None


def _coerce_content(node: dict[str, Any]) -> str | None:
    value = node.get("content")
    if isinstance(value, str):
        return value
    text_value = node.get("text")
    if isinstance(text_value, str):
        return text_value
    return None


def _coerce_bounding_box(value: object) -> list[float]:
    if not isinstance(value, list):
        return []
    bounding_box: list[float] = []
    for item in value:
        if isinstance(item, (int, float)):
            bounding_box.append(float(item))
    return bounding_box
