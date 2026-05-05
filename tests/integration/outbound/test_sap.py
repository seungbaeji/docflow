import pytest

from docflow_agent.errors import SapIntegrationError
from docflow_agent.outbound.external.sap import (
    SapClient,
    fetch_accounting_records,
    save_accounting_records,
)
from docflow_agent.types.external import SapRecord


def test_save_and_fetch_accounting_records() -> None:
    client = SapClient()
    records = [
        SapRecord(
            document_id="doc-001",
            company_code="1000",
            fiscal_year=2026,
            status="open",
            metadata={"source": "sap"},
        )
    ]

    save_accounting_records(client, "doc-001", records)

    assert fetch_accounting_records(client, "doc-001") == records


def test_fetch_accounting_records_raises_for_missing_document() -> None:
    with pytest.raises(SapIntegrationError, match="doc-missing"):
        fetch_accounting_records(SapClient(), "doc-missing")
