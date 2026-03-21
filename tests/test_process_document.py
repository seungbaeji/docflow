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
