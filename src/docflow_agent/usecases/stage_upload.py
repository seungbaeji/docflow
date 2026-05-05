"""Usecase facade for upload staging.

Uploads are staged as external files first. This facade writes the raw file,
records upload metadata, and updates the current session selection without
creating a source artifact yet.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from docflow_agent.ports.repositories import ArtifactRepository
from docflow_agent.ports.session_context import SessionDocumentStore
from docflow_agent.types.boundary.api import UploadResponse
from docflow_agent.workflow.document import source as document_source


def stage_upload(
    *,
    artifact_repository: ArtifactRepository,
    session_document_store: SessionDocumentStore,
    upload_dir: str,
    session_id: str | None,
    file_name: str,
    content_type: str,
    raw_file: bytes,
) -> UploadResponse:
    """Persist an uploaded file into staging storage and session context."""
    resolved_session_id = session_id or str(uuid4())
    resolved_upload_dir = Path(upload_dir).expanduser()
    resolved_upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4()}-{file_name}"
    stored_path = resolved_upload_dir / stored_name
    stored_path.write_bytes(raw_file)

    upload_id = document_source.stage_upload(
        artifact_repository,
        file_name=file_name,
        stored_path=str(stored_path.resolve()),
        content_type=content_type,
        size_bytes=len(raw_file),
    )
    session_document_store.set_current_upload_id(resolved_session_id, upload_id)
    session_document_store.clear_current_source_ref(resolved_session_id)

    return UploadResponse(
        session_id=resolved_session_id,
        upload_id=upload_id,
        file_name=file_name,
        stored_path=str(stored_path.resolve()),
        content_type=content_type,
        size_bytes=len(raw_file),
    )
