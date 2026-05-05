from __future__ import annotations

from dataclasses import dataclass

from docflow_agent.errors import OcrIntegrationError
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import OcrPage


@dataclass(frozen=True)
class OcrClient:
    engine_name: str = "stub"


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
