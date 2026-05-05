from docflow_agent.core.source_kind.detect import detect_source_kind
from docflow_agent.types.source import SourceRef, SpreadsheetSource


def test_detect_excel_source_kind() -> None:
    source = SpreadsheetSource(
        source_ref=SourceRef(
            name="invoice.xlsx",
            location="stub://fixtures/invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        ),
        sheet_names=["Invoice", "LineItems", "Summary"],
    )

    assert detect_source_kind(source) == "excel"
