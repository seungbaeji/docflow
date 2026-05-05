from docflow_agent.ports.session_context import SessionDocumentStore


class InMemorySessionDocumentStore(SessionDocumentStore):
    def __init__(self) -> None:
        self.source_refs_by_session: dict[str, str] = {}

    def set_current_source_ref(self, session_id: str, source_ref_id: str) -> None:
        self.source_refs_by_session[session_id] = source_ref_id

    def get_current_source_ref(self, session_id: str) -> str | None:
        return self.source_refs_by_session.get(session_id)

    def clear_current_source_ref(self, session_id: str) -> None:
        self.source_refs_by_session.pop(session_id, None)
