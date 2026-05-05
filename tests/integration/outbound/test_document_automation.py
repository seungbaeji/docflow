from docflow_agent.outbound.document_automation import apply_spreadsheet_edit_intents
from docflow_agent.types.edit import (
    CellValueEditIntent,
    InsertSheetEditIntent,
    RecalculateWorkbookEditIntent,
    SaveDocumentEditIntent,
)
from docflow_agent.types.source import SourceRef, SpreadsheetSource


def test_apply_spreadsheet_edit_intents_uses_file_strategy_by_default() -> None:
    source = SpreadsheetSource(
        source_ref=SourceRef(
            name="invoice.xlsx",
            location="stub://invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        ),
        sheet_names=["Invoice", "Summary"],
    )

    result = apply_spreadsheet_edit_intents(
        source=source,
        edit_intents=[
            CellValueEditIntent(sheet_name="Summary", cell_ref="B2", value="INV-001"),
            InsertSheetEditIntent(sheet_name="Audit"),
            SaveDocumentEditIntent(),
        ],
    )

    assert result.applied_count == 3
    assert result.strategy == "file_stub"


def test_apply_spreadsheet_edit_intents_uses_application_strategy_when_recalc_is_needed() -> None:
    source = SpreadsheetSource(
        source_ref=SourceRef(
            name="invoice.xlsx",
            location="stub://invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_system="ecm",
        ),
        sheet_names=["Invoice", "Summary"],
    )

    result = apply_spreadsheet_edit_intents(
        source=source,
        edit_intents=[RecalculateWorkbookEditIntent(full_rebuild=True)],
    )

    assert result.applied_count == 1
    assert result.strategy == "application_stub"
