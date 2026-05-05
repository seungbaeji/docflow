from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from docflow_agent.outbound.external.pdf import OpenDataLoaderPdfClient, extract_pdf_document
from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import WorkflowRunStore
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.common import FileInfo
from docflow_agent.types.boundary.external import PdfDocument
from docflow_agent.types.boundary.external import WorkflowRunRecord, VectorStoreDocument


@dataclass(frozen=True)
class UsecaseOutcome:
    ref_id: str
    message: str


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


def _extract_pdf_path(user_input: str) -> str | None:
    for token in user_input.replace('"', " ").replace("'", " ").split():
        candidate = Path(token.strip())
        if candidate.suffix.casefold() == ".pdf":
            return str(candidate)
    return None


@dataclass(frozen=True)
class RepositoryBackedDocumentUsecases:
    artifact_repository: ArtifactRepository
    llm_gateway: DocumentLlmPort | None = None
    workflow_run_store: WorkflowRunStore | None = None
    vector_store: VectorStorePort | None = None
    pdf_client: OpenDataLoaderPdfClient | None = None
    pdf_parser: Callable[[OpenDataLoaderPdfClient, FileInfo], PdfDocument] = extract_pdf_document

    def load_source(self, user_input: str) -> str:
        pdf_path = _extract_pdf_path(user_input)
        source_payload = {
            "prompt": user_input,
            "source_type": (
                "pdf"
                if pdf_path is not None
                else "excel"
                if _contains_any(user_input, ("excel", "엑셀", "document", "문서"))
                else "generic"
            ),
            "file_path": pdf_path,
        }
        return self.artifact_repository.save(
            kind="source",
            value=source_payload,
            metadata={"stage": "loaded"},
        )

    def register_uploaded_source(self, file_info: FileInfo) -> str:
        source_type = "pdf" if file_info.content_type == "application/pdf" else "generic"
        return self.artifact_repository.save(
            kind="source",
            value={
                "prompt": f"Uploaded file {file_info.name}",
                "source_type": source_type,
                "file_path": file_info.path,
                "file_name": file_info.name,
                "content_type": file_info.content_type,
                "uploaded": True,
            },
            metadata={"stage": "uploaded"},
        )

    def parse_units(self, source_ref_id: str) -> list[str]:
        source = self.artifact_repository.load("source", source_ref_id)
        prompt = str(source["prompt"])
        if source.get("source_type") == "pdf":
            return self._parse_pdf_units(source_ref_id=source_ref_id, source=source)
        unit_names = (
            ["settlement_sheet", "mail_targets"]
            if _contains_any(prompt, ("mail", "메일", "send", "보내", "미정산"))
            else ["document_main", "document_summary"]
        )
        unit_refs: list[str] = []
        for unit_name in unit_names:
            ref_id = self.artifact_repository.save(
                kind="unit",
                value={"name": unit_name, "source_ref_id": source_ref_id, "prompt": prompt},
                metadata={"source_ref_id": source_ref_id, "stage": "parsed"},
            )
            unit_refs.append(ref_id)
        return unit_refs

    def process_source_ref(self, source_ref_id: str) -> UsecaseOutcome:
        parsed_unit_ref_ids = self._get_existing_unit_refs(source_ref_id=source_ref_id, stage="parsed")
        if not parsed_unit_ref_ids:
            parsed_unit_ref_ids = self.parse_units(source_ref_id)

        categorized_unit_ref_ids = self.categorize_units(parsed_unit_ref_ids)
        bundle_ref_id = self.combine_bundle(categorized_unit_ref_ids)
        return self.analyze(bundle_ref_id)

    def build_document_context(self, source_ref_id: str) -> str:
        source = self.artifact_repository.load("source", source_ref_id)
        parsed_unit_ref_ids = self._get_existing_unit_refs(source_ref_id=source_ref_id, stage="parsed")
        if not parsed_unit_ref_ids:
            parsed_unit_ref_ids = self.parse_units(source_ref_id)

        unit_summaries: list[str] = []
        for unit_ref_id in parsed_unit_ref_ids[:3]:
            unit = self.artifact_repository.load("unit", unit_ref_id)
            content = unit.get("content")
            if isinstance(content, str) and content.strip():
                unit_summaries.append(content.strip())
            else:
                unit_summaries.append(str(unit.get("name", "document_unit")))

        return "\n".join(
            [
                f"source_type={source.get('source_type', 'unknown')}",
                f"file_path={source.get('file_path')}",
                "unit_summaries:",
                *[f"- {summary}" for summary in unit_summaries],
            ]
        )

    def _parse_pdf_units(self, *, source_ref_id: str, source: dict[str, object]) -> list[str]:
        file_path = source.get("file_path")
        if not isinstance(file_path, str) or self.pdf_client is None:
            return self._save_generic_pdf_units(source_ref_id=source_ref_id, source=source)

        file_info = FileInfo(
            name=Path(file_path).name,
            path=file_path,
            content_type="application/pdf",
        )
        parsed_document = self.pdf_parser(self.pdf_client, file_info)
        parsed_ref_id = self.artifact_repository.save(
            kind="analysis",
            value=parsed_document.model_dump(mode="python"),
            metadata={"source_ref_id": source_ref_id, "stage": "pdf_parsed"},
        )

        page_numbers = sorted(
            {
                element.page_number
                for element in parsed_document.elements
                if element.page_number is not None
            }
        )
        if not page_numbers:
            return self._save_generic_pdf_units(
                source_ref_id=source_ref_id,
                source=source,
                parsed_ref_id=parsed_ref_id,
                markdown=parsed_document.markdown,
            )

        unit_refs: list[str] = []
        for page_number in page_numbers:
            page_elements = [
                element for element in parsed_document.elements if element.page_number == page_number
            ]
            page_content = "\n".join(
                element.content for element in page_elements if element.content is not None
            )
            ref_id = self.artifact_repository.save(
                kind="unit",
                value={
                    "name": f"pdf_page_{page_number}",
                    "source_ref_id": source_ref_id,
                    "prompt": str(source["prompt"]),
                    "page_number": page_number,
                    "content": page_content,
                    "element_count": len(page_elements),
                    "parsed_ref_id": parsed_ref_id,
                },
                metadata={
                    "source_ref_id": source_ref_id,
                    "stage": "parsed",
                    "page_number": page_number,
                    "parsed_ref_id": parsed_ref_id,
                },
            )
            unit_refs.append(ref_id)
        return unit_refs

    def _save_generic_pdf_units(
        self,
        *,
        source_ref_id: str,
        source: dict[str, object],
        parsed_ref_id: str | None = None,
        markdown: str | None = None,
    ) -> list[str]:
        ref_id = self.artifact_repository.save(
            kind="unit",
            value={
                "name": "pdf_document",
                "source_ref_id": source_ref_id,
                "prompt": str(source["prompt"]),
                "content": markdown,
                "parsed_ref_id": parsed_ref_id,
            },
            metadata={
                "source_ref_id": source_ref_id,
                "stage": "parsed",
                "parsed_ref_id": parsed_ref_id,
            },
        )
        return [ref_id]

    def categorize_units(self, unit_ref_ids: list[str]) -> list[str]:
        categorized_refs: list[str] = []
        for unit_ref_id in unit_ref_ids:
            unit = self.artifact_repository.load("unit", unit_ref_id)
            categorized_ref_id = self.artifact_repository.save(
                kind="unit",
                value={
                    **unit,
                    "category": "invoice"
                    if _contains_any(str(unit["prompt"]), ("excel", "엑셀", "정산", "invoice"))
                    else "general",
                },
                metadata={"parent_unit_ref_id": unit_ref_id, "stage": "categorized"},
            )
            categorized_refs.append(categorized_ref_id)
        return categorized_refs

    def combine_bundle(self, unit_ref_ids: list[str]) -> str:
        units = [self.artifact_repository.load("unit", unit_ref_id) for unit_ref_id in unit_ref_ids]
        bundle = {
            "category": units[0].get("category", "general") if units else "general",
            "unit_ref_ids": unit_ref_ids,
            "source_ref_id": units[0]["source_ref_id"] if units else None,
        }
        return self.artifact_repository.save(
            kind="bundle",
            value=bundle,
            metadata={"stage": "combined"},
        )

    def analyze(self, bundle_ref_id: str) -> UsecaseOutcome:
        bundle = self.artifact_repository.load("bundle", bundle_ref_id)
        analysis_ref_id = self.artifact_repository.save(
            kind="analysis",
            value={
                "bundle_ref_id": bundle_ref_id,
                "unit_count": len(bundle["unit_ref_ids"]),
                "category": bundle["category"],
            },
            metadata={"bundle_ref_id": bundle_ref_id, "stage": "analyzed"},
        )
        self._save_workflow_run(
            record_id=analysis_ref_id,
            status="analyzed",
            artifact_refs=[bundle_ref_id, analysis_ref_id],
            metadata={"bundle_ref_id": bundle_ref_id, "category": str(bundle["category"])},
        )
        self._upsert_vector_document(
            document_id=analysis_ref_id,
            text=f"Analysis for {bundle_ref_id} category={bundle['category']}",
            metadata={"bundle_ref_id": bundle_ref_id, "kind": "analysis"},
        )
        return UsecaseOutcome(
            ref_id=analysis_ref_id,
            message=f"Document processed with {len(bundle['unit_ref_ids'])} categorized units.",
        )

    def filter_dataset(self, bundle_ref_id: str) -> str:
        dataset_ref_id = self.artifact_repository.save(
            kind="dataset",
            value={
                "bundle_ref_id": bundle_ref_id,
                "records": [{"status": "unsettled", "recipient": "ops@example.com"}],
            },
            metadata={"bundle_ref_id": bundle_ref_id, "stage": "filtered"},
        )
        return dataset_ref_id

    def compose_mail(self, dataset_ref_id: str) -> str:
        dataset = self.artifact_repository.load("dataset", dataset_ref_id)
        body = "Please review the unsettled items from the document workflow."
        if self.llm_gateway is not None:
            body = self.llm_gateway.summarize_document(
                {
                    "dataset_ref_id": dataset_ref_id,
                    "records": dataset["records"],
                    "task": "Compose an internal mail summary for unsettled items.",
                }
            )
        draft_ref_id = self.artifact_repository.save(
            kind="draft",
            value={
                "dataset_ref_id": dataset_ref_id,
                "to": ["ops@example.com"],
                "subject": "Unsettled items report",
                "body": body,
            },
            metadata={"dataset_ref_id": dataset_ref_id, "stage": "composed"},
        )
        return draft_ref_id

    def send_mail(self, draft_ref_id: str) -> UsecaseOutcome:
        result_ref_id = self.artifact_repository.save(
            kind="result",
            value={"draft_ref_id": draft_ref_id, "status": "sent"},
            metadata={"draft_ref_id": draft_ref_id, "stage": "sent"},
        )
        self._save_workflow_run(
            record_id=result_ref_id,
            status="sent",
            artifact_refs=[draft_ref_id, result_ref_id],
            metadata={"draft_ref_id": draft_ref_id},
        )
        return UsecaseOutcome(
            ref_id=result_ref_id,
            message="Mail sent after approval.",
        )

    def reject_send_mail(self, draft_ref_id: str | None) -> UsecaseOutcome:
        result_ref_id = self.artifact_repository.save(
            kind="result",
            value={"draft_ref_id": draft_ref_id, "status": "rejected"},
            metadata={"draft_ref_id": draft_ref_id, "stage": "rejected"},
        )
        self._save_workflow_run(
            record_id=result_ref_id,
            status="rejected",
            artifact_refs=[ref for ref in [draft_ref_id, result_ref_id] if ref is not None],
            metadata={"draft_ref_id": draft_ref_id},
        )
        return UsecaseOutcome(
            ref_id=result_ref_id,
            message="User rejected mail sending.",
        )

    def handle_unknown(self, user_input: str) -> UsecaseOutcome:
        result_ref_id = self.artifact_repository.save(
            kind="result",
            value={"prompt": user_input, "status": "unknown"},
            metadata={"stage": "unknown"},
        )
        self._save_workflow_run(
            record_id=result_ref_id,
            status="unknown",
            artifact_refs=[result_ref_id],
            metadata={"prompt": user_input},
        )
        return UsecaseOutcome(
            ref_id=result_ref_id,
            message="Unable to determine a supported workflow for the request.",
        )

    def _save_workflow_run(
        self,
        *,
        record_id: str,
        status: str,
        artifact_refs: list[str],
        metadata: dict[str, object],
    ) -> None:
        if self.workflow_run_store is None:
            return
        self.workflow_run_store.save_workflow_run(
            WorkflowRunRecord(
                record_id=record_id,
                status=status,
                artifact_refs=artifact_refs,
                metadata=metadata,
            )
        )

    def _upsert_vector_document(
        self,
        *,
        document_id: str,
        text: str,
        metadata: dict[str, object],
    ) -> None:
        if self.vector_store is None:
            return
        self.vector_store.upsert_documents(
            [
                VectorStoreDocument(
                    document_id=document_id,
                    text=text,
                    metadata=metadata,
                )
            ]
        )

    def _get_existing_unit_refs(self, *, source_ref_id: str, stage: str) -> list[str]:
        return self.artifact_repository.find(
            "unit",
            {"source_ref_id": source_ref_id, "stage": stage},
        )
