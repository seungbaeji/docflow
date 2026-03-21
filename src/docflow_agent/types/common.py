from dataclasses import dataclass


@dataclass(frozen=True)
class FileInfo:
    name: str
    path: str
    content_type: str
