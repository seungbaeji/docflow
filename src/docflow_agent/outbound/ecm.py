from docflow_agent.types.common import FileInfo


def fetch_from_ecm(document_id: str) -> FileInfo:
    raise NotImplementedError(f"ECM integration is stubbed for document_id={document_id}")
