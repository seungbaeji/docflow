from dataclasses import dataclass

from docflow_agent.types.common import FileInfo


@dataclass(frozen=True)
class SpreadsheetFile:
    file_info: FileInfo
    sheets: list[str]
