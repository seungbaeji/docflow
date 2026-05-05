from __future__ import annotations

from docflow_agent.errors import OcrIntegrationError
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import OcrPage


class OcrClient:
    def __init__(self, *, engine_name: str = "stub") -> None:
        self.engine_name = engine_name


def extract_text_pages(client: OcrClient, file_info: FileInfo) -> list[OcrPage]:
    if not file_info.name:
        raise OcrIntegrationError("<unknown>")
    del client
    return [
        OcrPage(
            page_number=1,
            text=f"OCR stub text extracted from {file_info.name}",
            confidence=0.99,
            metadata={"content_type": file_info.content_type},
        )
    ]
