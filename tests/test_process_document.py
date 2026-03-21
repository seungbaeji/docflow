from pytest import MonkeyPatch

from docflow_agent.types.documents import SpreadsheetFile
from docflow_agent.types.common import FileInfo
from docflow_agent.usecases.process_document import process_document


def test_process_document_orchestrates_excel_invoice_flow() -> None:
    result = process_document(
        FileInfo(
            name="invoice.xlsx",
            path="fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )

    assert result.document_type == "excel_invoice"
    assert result.success is True
    assert result.parsed_data["sheet_names"] == ["Invoice", "LineItems", "Summary"]
    assert result.parsed_data["invoice_rule_applied"] is True
    assert result.messages == ["Document processed successfully."]


def test_process_document_returns_controlled_failure_for_unsupported_type(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_load_spreadsheet(file_info: FileInfo) -> SpreadsheetFile:
        return SpreadsheetFile(
            file_info=file_info,
            sheets=["Cover"],
        )

    import docflow_agent.usecases.process_document as process_document_module

    monkeypatch.setattr(process_document_module, "load_spreadsheet", fake_load_spreadsheet)

    result = process_document(
        FileInfo(
            name="unknown.xlsx",
            path="stub://example/unknown.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )

    assert result.document_type == "unknown"
    assert result.success is False
    assert result.parsed_data == {}
    assert result.messages == ["Unsupported document type: unknown"]
