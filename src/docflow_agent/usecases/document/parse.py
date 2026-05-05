from __future__ import annotations

from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.value.document import ParsedDocumentPayload, ParsedUnitPayload, SourcePayload


def parse_source_payload(
    source: SourcePayload,
) -> tuple[ParsedDocumentPayload | None, list[ParsedUnitPayload]]:
    if source.source_type == "pdf":
        return None, [
            ParsedUnitPayload(
                name="pdf_document",
                prompt=source.prompt,
            )
        ]

    unit_names = (
        ["settlement_sheet", "mail_targets"]
        if _contains_any(source.prompt, ("mail", "메일", "send", "보내", "미정산"))
        else ["document_main", "document_summary"]
    )
    return None, [ParsedUnitPayload(name=name, prompt=source.prompt) for name in unit_names]


def parse_pdf_document_payload(
    source: SourcePayload,
    *,
    parsed_document: PdfDocument,
) -> tuple[ParsedDocumentPayload | None, list[ParsedUnitPayload]]:
    document_payload = ParsedDocumentPayload(
        file_name=parsed_document.file_name,
        page_count=parsed_document.page_count,
        markdown=parsed_document.markdown,
        text=parsed_document.text,
    )
    page_numbers = sorted(
        {
            element.page_number
            for element in parsed_document.elements
            if element.page_number is not None
        }
    )
    if not page_numbers:
        return document_payload, [
            ParsedUnitPayload(
                name="pdf_document",
                prompt=source.prompt,
                content=parsed_document.markdown,
            )
        ]

    units: list[ParsedUnitPayload] = []
    for page_number in page_numbers:
        page_elements = [
            element for element in parsed_document.elements if element.page_number == page_number
        ]
        page_content = "\n".join(
            element.content for element in page_elements if element.content is not None
        )
        units.append(
            ParsedUnitPayload(
                name=f"pdf_page_{page_number}",
                prompt=source.prompt,
                page_number=page_number,
                content=page_content,
                element_count=len(page_elements),
            )
        )
    return document_payload, units


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)
