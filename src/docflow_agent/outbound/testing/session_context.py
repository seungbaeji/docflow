from dataclasses import dataclass, field

from docflow_agent.ports.session_context import SessionDocumentStore


@dataclass
class InMemorySessionDocumentStore(SessionDocumentStore):
    source_refs_by_session: dict[str, str] = field(default_factory=dict)

    def set_current_source_ref(self, session_id: str, source_ref_id: str) -> None:
        self.source_refs_by_session[session_id] = source_ref_id

    def get_current_source_ref(self, session_id: str) -> str | None:
        return self.source_refs_by_session.get(session_id)

    def clear_current_source_ref(self, session_id: str) -> None:
        self.source_refs_by_session.pop(session_id, None)
