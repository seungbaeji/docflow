from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.usecases.document import (
    categorize_unit_payloads,
    combine_unit_payloads,
    parse_pdf_document_payload,
    parse_source_payload,
)
from docflow_agent.workflow.document.support import (
    find_artifact_refs,
    load_categorized_unit_payload,
    load_parsed_unit_payload,
    load_source_payload,
    load_source_ref_from_unit,
)

PdfParser = Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument]


def parse_units(
    artifact_repository: ArtifactRepository,
    *,
    source_ref_id: str,
    pdf_client: OpenDataLoaderPdfClient | None,
    pdf_parser: PdfParser,
) -> list[str]:
    source = load_source_payload(artifact_repository, source_ref_id)
    existing_refs = find_artifact_refs(
        artifact_repository,
        kind="unit",
        filters={"source_ref_id": source_ref_id, "stage": "parsed"},
    )
    if existing_refs:
        return existing_refs

    parsed_document, parsed_units = parse_source_payload(source)
    if source.source_type == "pdf" and source.file_path is not None and pdf_client is not None:
        file_info = FileInfo(
            name=source.file_name or Path(source.file_path).name,
            path=source.file_path,
            content_type=source.content_type or "application/pdf",
        )
        extracted_pdf = pdf_parser(pdf_client, file_info)
        parsed_document, parsed_units = parse_pdf_document_payload(
            source,
            parsed_document=extracted_pdf,
        )
    parsed_ref_id: str | None = None
    if parsed_document is not None:
        parsed_ref_id = artifact_repository.save(
            kind="analysis",
            value=asdict(parsed_document),
            metadata={"source_ref_id": source_ref_id, "stage": "pdf_parsed"},
        )
    unit_ref_ids: list[str] = []
    for unit in parsed_units:
        metadata: dict[str, object] = {"source_ref_id": source_ref_id, "stage": "parsed"}
        if unit.page_number is not None:
            metadata["page_number"] = unit.page_number
        if parsed_ref_id is not None:
            metadata["parsed_ref_id"] = parsed_ref_id
        unit_ref_ids.append(
            artifact_repository.save(
                kind="unit",
                value={
                    **asdict(unit),
                    "source_ref_id": source_ref_id,
                    "parsed_ref_id": parsed_ref_id,
                },
                metadata=metadata,
            )
        )
    return unit_ref_ids


def categorize_units(
    artifact_repository: ArtifactRepository,
    *,
    unit_ref_ids: list[str],
) -> list[str]:
    categorized_refs: list[str] = []
    units = [load_parsed_unit_payload(artifact_repository, unit_ref_id) for unit_ref_id in unit_ref_ids]
    categorized_units = categorize_unit_payloads(units)
    for parent_ref_id, categorized_unit in zip(unit_ref_ids, categorized_units, strict=True):
        source_ref_id = load_source_ref_from_unit(artifact_repository, parent_ref_id)
        categorized_refs.append(
            artifact_repository.save(
                kind="unit",
                value={
                    **asdict(categorized_unit),
                    "source_ref_id": source_ref_id,
                },
                metadata={
                    "parent_unit_ref_id": parent_ref_id,
                    "source_ref_id": source_ref_id,
                    "stage": "categorized",
                },
            )
        )
    return categorized_refs


def combine_bundle(
    artifact_repository: ArtifactRepository,
    *,
    unit_ref_ids: list[str],
) -> str:
    units = [load_categorized_unit_payload(artifact_repository, unit_ref_id) for unit_ref_id in unit_ref_ids]
    source_ref_id = load_source_ref_from_unit(artifact_repository, unit_ref_ids[0]) if unit_ref_ids else None
    bundle = combine_unit_payloads(units, unit_ref_ids=unit_ref_ids, source_ref_id=source_ref_id)
    return artifact_repository.save(
        kind="bundle",
        value=asdict(bundle),
        metadata={"stage": "combined", "source_ref_id": source_ref_id},
    )
