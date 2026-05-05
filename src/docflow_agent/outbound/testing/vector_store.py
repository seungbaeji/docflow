from dataclasses import dataclass, field

from docflow_agent.ports.vector_store import VectorStorePort
from docflow_agent.types.boundary.external import VectorSearchHit, VectorStoreDocument


def _tokenize(text: str) -> set[str]:
    return {token for token in text.casefold().split() if token}


@dataclass
class InMemoryVectorStore(VectorStorePort):
    documents: dict[str, VectorStoreDocument] = field(default_factory=dict)

    def upsert_documents(self, documents: list[VectorStoreDocument]) -> None:
        for document in documents:
            self.documents[document.document_id] = document

    def search_similar(
        self,
        query_text: str,
        *,
        limit: int = 5,
    ) -> list[VectorSearchHit]:
        query_tokens = _tokenize(query_text)
        hits: list[VectorSearchHit] = []
        for document in self.documents.values():
            document_tokens = _tokenize(document.text)
            if not query_tokens or not document_tokens:
                score = 0.0
            else:
                overlap = len(query_tokens & document_tokens)
                score = overlap / len(query_tokens)
            hits.append(
                VectorSearchHit(
                    document_id=document.document_id,
                    score=score,
                    metadata=document.metadata,
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    def delete_document(self, document_id: str) -> None:
        self.documents.pop(document_id, None)
