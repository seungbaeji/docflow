from docflow_agent.types.edit import (
    CellValueEditIntent,
    EditExecutionResult,
    InsertSheetEditIntent,
    RecalculateWorkbookEditIntent,
    SaveDocumentEditIntent,
)
from docflow_agent.types.source import SpreadsheetSource


def apply_spreadsheet_edit_intents(
    source: SpreadsheetSource,
    edit_intents: list[
        CellValueEditIntent
        | InsertSheetEditIntent
        | RecalculateWorkbookEditIntent
        | SaveDocumentEditIntent
    ],
) -> EditExecutionResult:
    # Stub executor for local testing. Real file-level and app-level automation stays here.
    _ = source
    strategy = _choose_execution_strategy(edit_intents)
    return EditExecutionResult(
        applied_count=len(edit_intents),
        strategy=strategy,
    )


def _choose_execution_strategy(
    edit_intents: list[
        CellValueEditIntent
        | InsertSheetEditIntent
        | RecalculateWorkbookEditIntent
        | SaveDocumentEditIntent
    ],
) -> str:
    if any(isinstance(intent, RecalculateWorkbookEditIntent) for intent in edit_intents):
        return "application_stub"
    return "file_stub"
