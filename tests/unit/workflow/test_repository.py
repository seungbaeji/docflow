import pytest

from docflow_agent.outbound.testing.repositories.in_memory_artifact_repository import (
    InMemoryArtifactRepository,
)


def test_repository_save_and_load_artifact() -> None:
    repository = InMemoryArtifactRepository()

    ref_id = repository.save("source", {"name": "invoice.xlsx"}, metadata={"flow": "document"})

    assert repository.load("source", ref_id) == {"name": "invoice.xlsx"}


def test_repository_missing_artifact_raises_clear_error() -> None:
    repository = InMemoryArtifactRepository()

    with pytest.raises(KeyError, match="Artifact not found"):
        repository.load("bundle", "bundle-9999")


def test_repository_find_filters_by_metadata() -> None:
    repository = InMemoryArtifactRepository()
    matching_ref = repository.save("unit", {"name": "sheet-1"}, metadata={"stage": "parsed"})
    repository.save("unit", {"name": "sheet-2"}, metadata={"stage": "categorized"})

    assert repository.find("unit", {"stage": "parsed"}) == [matching_ref]
