from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.types.boundary.external import VectorStoreDocument


def test_vector_store_returns_ranked_hits() -> None:
    store = InMemoryVectorStore()
    store.upsert_documents(
        [
            VectorStoreDocument(
                document_id="doc-001",
                text="invoice settlement approval",
                metadata={"source": "ecm"},
            ),
            VectorStoreDocument(
                document_id="doc-002",
                text="holiday schedule announcement",
                metadata={"source": "mail"},
            ),
        ]
    )

    hits = store.search_similar("invoice approval", limit=1)

    assert len(hits) == 1
    assert hits[0].document_id == "doc-001"
    assert hits[0].score > 0.0


def test_vector_store_can_delete_documents() -> None:
    store = InMemoryVectorStore()
    store.upsert_documents(
        [VectorStoreDocument(document_id="doc-001", text="invoice", metadata={})]
    )

    store.delete_document("doc-001")

    assert store.search_similar("invoice") == []
