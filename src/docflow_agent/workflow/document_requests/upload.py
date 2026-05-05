from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from docflow_agent.bootstrap import AppContainer
from docflow_agent.types.boundary.api import UploadResponse
from docflow_agent.workflow.document import source as document_source


def stage_uploaded_document(
    *,
    container: AppContainer,
    session_id: str | None,
    file_name: str,
    content_type: str,
    raw_file: bytes,
) -> UploadResponse:
    resolved_session_id = session_id or str(uuid4())
    upload_dir = Path(container.settings.app.upload_dir).expanduser()
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4()}-{file_name}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(raw_file)

    upload_id = document_source.stage_upload(
        container.artifact_repository,
        file_name=file_name,
        stored_path=str(stored_path.resolve()),
        content_type=content_type,
        size_bytes=len(raw_file),
    )
    container.session_document_store.set_current_upload_id(resolved_session_id, upload_id)
    container.session_document_store.clear_current_source_ref(resolved_session_id)

    return UploadResponse(
        session_id=resolved_session_id,
        upload_id=upload_id,
        file_name=file_name,
        stored_path=str(stored_path.resolve()),
        content_type=content_type,
        size_bytes=len(raw_file),
    )
