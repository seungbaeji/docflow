from __future__ import annotations

from dataclasses import dataclass

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.rdbms import ProcessingRecordPort
from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.external import ProcessingRecord, VectorStoreDocument


@dataclass(frozen=True)
class UsecaseOutcome:
    ref_id: str
    message: str


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(keyword in lowered for keyword in keywords)


@dataclass(frozen=True)
class RepositoryBackedDocumentUsecases:
    artifact_repository: ArtifactRepository
    llm_gateway: DocumentLlmPort | None = None
    processing_record_store: ProcessingRecordPort | None = None
    vector_store: VectorStorePort | None = None

    def load_source(self, user_input: str) -> str:
        source_payload = {
            "prompt": user_input,
            "source_type": "excel"
            if _contains_any(user_input, ("excel", "엑셀", "document", "문서"))
            else "generic",
        }
        return self.artifact_repository.save(
            kind="source",
            value=source_payload,
            metadata={"stage": "loaded"},
        )

    def parse_units(self, source_ref_id: str) -> list[str]:
        source = self.artifact_repository.load("source", source_ref_id)
        prompt = str(source["prompt"])
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
        self._save_processing_record(
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
        self._save_processing_record(
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
        self._save_processing_record(
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
        self._save_processing_record(
            record_id=result_ref_id,
            status="unknown",
            artifact_refs=[result_ref_id],
            metadata={"prompt": user_input},
        )
        return UsecaseOutcome(
            ref_id=result_ref_id,
            message="Unable to determine a supported workflow for the request.",
        )

    def _save_processing_record(
        self,
        *,
        record_id: str,
        status: str,
        artifact_refs: list[str],
        metadata: dict[str, object],
    ) -> None:
        if self.processing_record_store is None:
            return
        self.processing_record_store.save_processing_record(
            ProcessingRecord(
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
