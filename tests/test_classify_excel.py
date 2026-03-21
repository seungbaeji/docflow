from docflow_agent.core.classify.document import classify_document
from docflow_agent.types.common import FileInfo
from docflow_agent.types.documents import SpreadsheetFile


def test_classify_excel_invoice() -> None:
    document = SpreadsheetFile(
        file_info=FileInfo(
            name="invoice.xlsx",
            path="fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        sheets=["Invoice", "LineItems", "Summary"],
    )

    assert classify_document(document) == "excel_invoice"
