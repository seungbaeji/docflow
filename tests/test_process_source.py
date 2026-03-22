from pytest import MonkeyPatch
import pytest
from typing import cast

from docflow_agent.errors import UnsupportedCategoryError
from docflow_agent.types.source import SourceRef, SpreadsheetSource
from docflow_agent.usecases.process_source import process_source


def test_process_source_orchestrates_excel_invoice_flow() -> None:
    result = process_source(
        SourceRef(
            name="invoice.xlsx",
            location="stub://fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        )
    )

    assert result.source_kind == "excel"
    assert result.category == "invoice"
    assert result.success is True
    assert result.unit_count == 3
    bundle = cast(dict[str, object], result.bundle_data["bundle"])
    analysis = cast(dict[str, object], result.bundle_data["analysis"])
    assert bundle["invoice_number"] == "INV-001"
    assert analysis["unit_names"] == ["Invoice", "LineItems", "Summary"]
    assert result.messages == ["Source processed successfully."]


def test_process_source_raises_for_unknown_category(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_load_spreadsheet_source(source_ref: SourceRef) -> SpreadsheetSource:
        return SpreadsheetSource(
            source_ref=source_ref,
            sheet_names=["Cover"],
        )

    import docflow_agent.usecases.process_source as process_source_module

    monkeypatch.setattr(
        process_source_module,
        "load_spreadsheet_source",
        fake_load_spreadsheet_source,
    )

    with pytest.raises(UnsupportedCategoryError, match="Unsupported category: unknown"):
        process_source(
            SourceRef(
                name="unknown.xlsx",
                location="stub://example/unknown.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                source_system="ecm",
            )
        )
