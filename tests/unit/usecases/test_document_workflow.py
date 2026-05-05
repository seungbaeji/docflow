from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.outbound.testing.rdbms import InMemoryProcessingRecordStore
from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)
from docflow_agent.outbound.testing.vector_store import InMemoryVectorStore
from docflow_agent.usecases.document_workflow import RepositoryBackedDocumentUsecases


def test_analyze_persists_record_and_vector_document() -> None:
    repository = InMemoryArtifactRepository()
    processing_store = InMemoryProcessingRecordStore()
    vector_store = InMemoryVectorStore()
    usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=repository,
        processing_record_store=processing_store,
        vector_store=vector_store,
    )

    bundle_ref_id = repository.save(
        "bundle",
        {
            "category": "invoice",
            "unit_ref_ids": ["unit-001", "unit-002"],
            "source_ref_id": "source-001",
        },
        metadata={"stage": "combined"},
    )

    outcome = usecases.analyze(bundle_ref_id)

    record = processing_store.load_processing_record(outcome.ref_id)
    assert record.status == "analyzed"
    assert record.artifact_refs == [bundle_ref_id, outcome.ref_id]
    hits = vector_store.search_similar("analysis invoice", limit=1)
    assert hits
    assert hits[0].document_id == outcome.ref_id


def test_compose_mail_uses_llm_gateway_when_available() -> None:
    repository = InMemoryArtifactRepository()
    llm_gateway = StubDocumentLlmGateway(summary_response="LLM generated mail body")
    usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=repository,
        llm_gateway=llm_gateway,
    )

    dataset_ref_id = repository.save(
        "dataset",
        {
            "bundle_ref_id": "bundle-001",
            "records": [{"status": "unsettled", "recipient": "ops@example.com"}],
        },
        metadata={"stage": "filtered"},
    )

    draft_ref_id = usecases.compose_mail(dataset_ref_id)

    draft = repository.load("draft", draft_ref_id)
    assert draft["body"] == "LLM generated mail body"
    assert llm_gateway.summarized_payloads


def test_send_mail_persists_record() -> None:
    repository = InMemoryArtifactRepository()
    processing_store = InMemoryProcessingRecordStore()
    usecases = RepositoryBackedDocumentUsecases(
        artifact_repository=repository,
        processing_record_store=processing_store,
    )

    draft_ref_id = repository.save(
        "draft",
        {"dataset_ref_id": "dataset-001", "to": ["ops@example.com"]},
        metadata={"stage": "composed"},
    )

    outcome = usecases.send_mail(draft_ref_id)

    record = processing_store.load_processing_record(outcome.ref_id)
    assert record.status == "sent"
