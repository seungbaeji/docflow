from __future__ import annotations

from docflow_agent.types.value.document import (
    AnalysisPayload,
    DocumentPayload,
    DocumentQuestionPayload,
    ParsedDocumentPayload,
    ParsedUnitPayload,
    SourcePayload,
)


def build_payload(
    *,
    source_ref_id: str,
    source: SourcePayload,
    parsed_document: ParsedDocumentPayload | None,
    parsed_units: list[ParsedUnitPayload],
    parsed_unit_ref_ids: list[str],
    analysis: AnalysisPayload | dict[str, object] | None = None,
) -> DocumentPayload:
    unit_summaries: list[str] = []
    for unit in parsed_units[:3]:
        if unit.content is not None and unit.content.strip():
            summary = unit.content.strip()
        else:
            summary = unit.name
        unit_summaries.append(summary[:400])

    markdown = parsed_document.markdown if parsed_document is not None else None
    markdown_excerpt = markdown.strip()[:800] if markdown is not None and markdown.strip() else None

    return DocumentPayload(
        source_ref_id=source_ref_id,
        source_type=source.source_type,
        file_name=source.file_name or (parsed_document.file_name if parsed_document else ""),
        file_path=source.file_path or "",
        page_count=parsed_document.page_count if parsed_document is not None else 0,
        unit_count=len(parsed_units),
        unit_summaries=unit_summaries,
        parsed_unit_ref_ids=list(parsed_unit_ref_ids),
        markdown=markdown,
        text=parsed_document.text if parsed_document is not None else None,
        markdown_excerpt=markdown_excerpt,
        analysis=analysis if isinstance(analysis, dict) else None,
    )


def build_context(payload: DocumentPayload) -> str:
    return "\n".join(
        [
            f"source_type={payload.source_type}",
            f"file_name={payload.file_name}",
            f"file_path={payload.file_path}",
            f"page_count={payload.page_count}",
            f"unit_count={payload.unit_count}",
            "unit_summaries:",
            *[f"- {summary}" for summary in payload.unit_summaries],
        ]
    )


def render_summary(payload: DocumentPayload) -> str:
    preview_items = [f"- {summary}" for summary in payload.unit_summaries if summary.strip()]
    preview_text = "\n".join(preview_items) if preview_items else "- 추출된 본문이 없습니다."
    page_count_line = (
        f"- 감지된 페이지 수: {payload.page_count}"
        if payload.page_count > 0
        else "- 감지된 페이지 수: 확인되지 않음"
    )
    excerpt_line = ""
    if payload.markdown_excerpt is not None and payload.markdown_excerpt.strip():
        excerpt_line = f"\n- 문서 미리보기:\n{payload.markdown_excerpt[:500]}"
    return (
        "문서 분석을 완료했습니다.\n"
        f"- 문서 유형: {payload.source_type}\n"
        f"- 파일명: {payload.file_name}\n"
        f"{page_count_line}\n"
        f"- 추출된 단위 수: {payload.unit_count}\n"
        "- 추출된 핵심 내용:\n"
        f"{preview_text}"
        f"{excerpt_line}"
    )


def build_question_payload(
    question: str,
    payload: DocumentPayload,
) -> DocumentQuestionPayload:
    return DocumentQuestionPayload(question=question, document=payload)
