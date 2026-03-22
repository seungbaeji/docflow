from docflow_agent.types.edit import CellValueEditIntent, EditExecutionResult
from docflow_agent.types.source import SpreadsheetSource


def apply_spreadsheet_edit_intents(
    source: SpreadsheetSource,
    edit_intents: list[CellValueEditIntent],
) -> EditExecutionResult:
    # Stub execution for local testing. Real file or application automation stays here.
    _ = source
    return EditExecutionResult(
        applied_count=len(edit_intents),
        strategy="file_stub",
    )
