"""Application errors."""


class AppError(Exception):
    """Base application error."""


class UnsupportedDocumentError(AppError):
    """Raised when a document type is not supported."""
