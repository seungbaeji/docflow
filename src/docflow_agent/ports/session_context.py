from typing import Protocol


class SessionDocumentStore(Protocol):
    def set_current_source_ref(self, session_id: str, source_ref_id: str) -> None:
        ...

    def get_current_source_ref(self, session_id: str) -> str | None:
        ...

    def clear_current_source_ref(self, session_id: str) -> None:
        ...
