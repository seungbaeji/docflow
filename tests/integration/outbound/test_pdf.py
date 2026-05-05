import sys
import types
from pathlib import Path

import pytest

from docflow_agent.errors import MissingPdfDependencyError, PdfIntegrationError
import docflow_agent.outbound.external.pdf as pdf_adapter
from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient, extract_pdf_document
from docflow_agent.types.boundary.common import FileInfo


def test_extract_pdf_document_uses_opendataloader_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "invoice.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")
    captured_kwargs: dict[str, object] = {}

    def fake_convert(**kwargs: object) -> None:
        captured_kwargs.update(kwargs)
        output_dir = Path(str(kwargs["output_dir"]))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "invoice.md").write_text("# Invoice\nAmount due", encoding="utf-8")
        (output_dir / "invoice.json").write_text(
            (
                "{"
                '"file name":"invoice.pdf",'
                '"number of pages":2,'
                '"title":"Invoice",'
                '"kids":['
                '{"type":"heading","page number":1,"bounding box":[72,700,540,730],"content":"Invoice"},'
                '{"type":"paragraph","page number":1,"bounding box":[72,640,540,680],"content":"Amount due"}'
                "]}"
            ),
            encoding="utf-8",
        )

    monkeypatch.setitem(sys.modules, "opendataloader_pdf", types.SimpleNamespace(convert=fake_convert))

    document = extract_pdf_document(
        OpenDataLoaderPdfClient(use_struct_tree=True),
        FileInfo(
            name="invoice.pdf",
            path=str(source_path),
            content_type="application/pdf",
        ),
    )

    assert captured_kwargs["input_path"] == [str(source_path)]
    assert captured_kwargs["format"] == "markdown,json"
    assert captured_kwargs["use_struct_tree"] is True
    assert document.file_name == "invoice.pdf"
    assert document.page_count == 2
    assert document.markdown == "# Invoice\nAmount due"
    assert len(document.elements) == 2
    assert document.elements[0].element_type == "heading"
    assert document.elements[0].bounding_box == [72.0, 700.0, 540.0, 730.0]


def test_extract_pdf_document_requires_optional_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "invoice.pdf"
    source_path.write_bytes(b"%PDF-1.7 fake")
    monkeypatch.setattr(
        pdf_adapter,
        "_import_opendataloader_pdf",
        lambda: (_ for _ in ()).throw(MissingPdfDependencyError("opendataloader-pdf")),
    )

    with pytest.raises(MissingPdfDependencyError, match="opendataloader-pdf"):
        extract_pdf_document(
            OpenDataLoaderPdfClient(),
            FileInfo(
                name="invoice.pdf",
                path=str(source_path),
                content_type="application/pdf",
            ),
        )


def test_extract_pdf_document_rejects_non_pdf_content_type(tmp_path: Path) -> None:
    source_path = tmp_path / "invoice.txt"
    source_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(PdfIntegrationError, match="content_type must be application/pdf"):
        extract_pdf_document(
            OpenDataLoaderPdfClient(),
            FileInfo(
                name="invoice.txt",
                path=str(source_path),
                content_type="text/plain",
            ),
        )
