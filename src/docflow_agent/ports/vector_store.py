from typing import Protocol

from docflow_agent.types.boundary.external import VectorSearchHit, VectorStoreDocument


class VectorStorePort(Protocol):
    def upsert_documents(self, documents: list[VectorStoreDocument]) -> None:
        ...

    def search_similar(
        self,
        query_text: str,
        *,
        limit: int = 5,
    ) -> list[VectorSearchHit]:
        ...

    def delete_document(self, document_id: str) -> None:
        ...
