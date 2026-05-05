"""Processing and classification errors."""

from docflow_agent.errors.base import DocflowError


class ProcessingError(DocflowError):
    """Base error for source processing failures."""


class UnsupportedSourceKindError(ProcessingError):
    def __init__(self, source_kind: str) -> None:
        super().__init__(f"Unsupported source kind: {source_kind}")
        self.source_kind = source_kind


class UnsupportedCategoryError(ProcessingError):
    def __init__(self, category: str) -> None:
        super().__init__(f"Unsupported category: {category}")
        self.category = category
