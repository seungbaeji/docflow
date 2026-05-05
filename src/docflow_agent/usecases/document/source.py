from __future__ import annotations

from pathlib import Path
from typing import Literal

from docflow_agent.types.value.document import SourcePayload, UploadPayload


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


def _extract_pdf_path(user_input: str) -> str | None:
    for token in user_input.replace('"', " ").replace("'", " ").split():
        candidate = Path(token.strip())
        if candidate.suffix.casefold() == ".pdf":
            return str(candidate)
    return None


def build_source_payload_from_prompt(user_input: str) -> SourcePayload:
    pdf_path = _extract_pdf_path(user_input)
    source_type: Literal["pdf", "excel", "generic"]
    if pdf_path is not None:
        source_type = "pdf"
    elif _contains_any(user_input, ("excel", "엑셀", "document", "문서")):
        source_type = "excel"
    else:
        source_type = "generic"
    return SourcePayload(
        prompt=user_input,
        source_type=source_type,
        file_path=pdf_path,
        file_name=Path(pdf_path).name if pdf_path is not None else None,
    )


def build_source_payload_from_upload(upload: UploadPayload) -> SourcePayload:
    source_type: Literal["pdf", "excel", "generic"] = (
        "pdf" if upload.content_type == "application/pdf" else "generic"
    )
    return SourcePayload(
        prompt=f"Uploaded file {upload.file_name}",
        source_type=source_type,
        file_path=upload.stored_path,
        file_name=upload.file_name,
        content_type=upload.content_type,
        uploaded=True,
    )
