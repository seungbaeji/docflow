from __future__ import annotations

from typing import Literal

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.document import DatasetPayload, MailDraftPayload, MailResultPayload


def build_dataset_payload() -> DatasetPayload:
    return DatasetPayload(
        records=[{"status": "unsettled", "recipient": "ops@example.com"}]
    )


def build_mail_draft_payload(
    dataset: DatasetPayload,
    *,
    llm_gateway: DocumentLlmPort | None = None,
) -> MailDraftPayload:
    body = "Please review the unsettled items from the document workflow."
    if llm_gateway is not None:
        body = llm_gateway.summarize_document(
            {
                "records": dataset.records,
                "task": "Compose an internal mail summary for unsettled items.",
            }
        )
    return MailDraftPayload(
        recipients=["ops@example.com"],
        subject="Unsettled items report",
        body=body,
    )


def build_mail_result_payload(
    draft_ref_id: str | None,
    *,
    status: str,
) -> MailResultPayload:
    normalized_status: Literal["sent", "rejected"] = "sent" if status == "sent" else "rejected"
    return MailResultPayload(
        draft_ref_id=draft_ref_id,
        status=normalized_status,
    )
