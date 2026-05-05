from __future__ import annotations

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.usecases.document import (
    build_source_payload_from_prompt,
    build_source_payload_from_upload,
)
from docflow_agent.workflow.document.support import (
    load_upload_payload,
    save_source_payload,
)


def stage_upload(
    artifact_repository: ArtifactRepository,
    *,
    file_name: str,
    stored_path: str,
    content_type: str,
    size_bytes: int,
) -> str:
    return artifact_repository.save(
        kind="upload",
        value={
            "upload_id": None,
            "file_name": file_name,
            "stored_path": stored_path,
            "content_type": content_type,
            "size_bytes": size_bytes,
        },
        metadata={"stage": "uploaded"},
    )


def load_source(artifact_repository: ArtifactRepository, *, user_input: str) -> str:
    payload = build_source_payload_from_prompt(user_input)
    return save_source_payload(artifact_repository, payload, stage="loaded")


def source_from_upload(artifact_repository: ArtifactRepository, *, upload_id: str) -> str:
    upload = load_upload_payload(artifact_repository, upload_id)
    payload = build_source_payload_from_upload(upload)
    return save_source_payload(
        artifact_repository,
        payload,
        stage="uploaded_source",
        metadata={"upload_id": upload_id},
    )
