from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from docflow_agent.errors import (
    DocflowError,
    EcmRequestError,
    EcmResponseError,
    MailIntegrationError,
    UnsupportedCategoryError,
    UnsupportedLlmProviderError,
    UnsupportedSourceKindError,
)
from docflow_agent.types.source import SourceRef
from docflow_agent.usecases.process_source import process_source

router = APIRouter()


class ProcessRequest(BaseModel):
    source_name: str
    source_location: str
    source_system: str = "ecm"
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/process")
def process(request: ProcessRequest) -> dict[str, object]:
    try:
        result = process_source(
            SourceRef(
                name=request.source_name,
                location=request.source_location,
                content_type=request.content_type,
                source_system=request.source_system,
            )
        )
    except (UnsupportedSourceKindError, UnsupportedCategoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (EcmRequestError, EcmResponseError, MailIntegrationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except UnsupportedLlmProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except DocflowError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "source_kind": result.source_kind,
        "category": result.category,
        "success": result.success,
        "unit_count": result.unit_count,
        "bundle_data": result.bundle_data,
        "messages": result.messages,
    }
