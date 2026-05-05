from langgraph.store.base import BaseStore

from docflow_agent.ports.session_context import SessionDocumentStore


class StoreBackedSessionDocumentStore(SessionDocumentStore):
    def __init__(self, store: BaseStore) -> None:
        self.store = store

    def set_current_upload_id(self, session_id: str, upload_id: str) -> None:
        self.store.put(
            ("session_documents", session_id),
            "current_upload_id",
            {"upload_id": upload_id},
        )

    def get_current_upload_id(self, session_id: str) -> str | None:
        item = self.store.get(("session_documents", session_id), "current_upload_id")
        if item is None:
            return None
        upload_id = item.value.get("upload_id")
        return upload_id if isinstance(upload_id, str) else None

    def clear_current_upload_id(self, session_id: str) -> None:
        self.store.delete(("session_documents", session_id), "current_upload_id")

    def set_current_source_ref(self, session_id: str, source_ref_id: str) -> None:
        self.store.put(
            ("session_documents", session_id),
            "current_source_ref",
            {"source_ref_id": source_ref_id},
        )

    def get_current_source_ref(self, session_id: str) -> str | None:
        item = self.store.get(("session_documents", session_id), "current_source_ref")
        if item is None:
            return None
        source_ref_id = item.value.get("source_ref_id")
        return source_ref_id if isinstance(source_ref_id, str) else None

    def clear_current_source_ref(self, session_id: str) -> None:
        self.store.delete(("session_documents", session_id), "current_source_ref")
