from __future__ import annotations

from docflow_agent.types.value.document import (
    AnalysisPayload,
    BundlePayload,
    CategorizedUnitPayload,
    ParsedUnitPayload,
)


def categorize_unit_payloads(units: list[ParsedUnitPayload]) -> list[CategorizedUnitPayload]:
    categorized: list[CategorizedUnitPayload] = []
    for unit in units:
        category = (
            "invoice"
            if _contains_any(unit.prompt, ("excel", "엑셀", "정산", "invoice"))
            else "general"
        )
        categorized.append(
            CategorizedUnitPayload(
                name=unit.name,
                prompt=unit.prompt,
                category=category,
                page_number=unit.page_number,
                content=unit.content,
                element_count=unit.element_count,
            )
        )
    return categorized


def combine_unit_payloads(
    units: list[CategorizedUnitPayload],
    *,
    unit_ref_ids: list[str],
    source_ref_id: str | None,
) -> BundlePayload:
    category = units[0].category if units else "general"
    return BundlePayload(
        category=category,
        unit_ref_ids=list(unit_ref_ids),
        source_ref_id=source_ref_id,
    )


def analyze_bundle_payload(bundle: BundlePayload) -> AnalysisPayload:
    return AnalysisPayload(
        bundle_ref_id=bundle.source_ref_id or "",
        unit_count=len(bundle.unit_ref_ids),
        category=bundle.category,
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)
