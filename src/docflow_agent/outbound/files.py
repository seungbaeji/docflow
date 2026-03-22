from docflow_agent.types.source import SourceRef, SpreadsheetSource


def load_spreadsheet_source(source_ref: SourceRef) -> SpreadsheetSource:
    # Stub source loading with deterministic sheet names for local testing.
    return SpreadsheetSource(
        source_ref=source_ref,
        sheet_names=["Invoice", "LineItems", "Summary"],
    )
