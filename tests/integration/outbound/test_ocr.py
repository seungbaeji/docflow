from docflow_agent.outbound.external.ocr import OcrClient, extract_text_pages
from docflow_agent.types.common import FileInfo


def test_extract_text_pages_returns_stub_ocr_result() -> None:
    pages = extract_text_pages(
        OcrClient(),
        FileInfo(
            name="invoice.pdf",
            path="/tmp/invoice.pdf",
            content_type="application/pdf",
        ),
    )

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "invoice.pdf" in pages[0].text
    assert pages[0].confidence == 0.99
