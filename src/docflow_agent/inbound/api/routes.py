from fastapi import APIRouter
from pydantic import BaseModel

from docflow_agent.types.common import FileInfo
from docflow_agent.usecases.process_document import process_document

router = APIRouter()


class ProcessRequest(BaseModel):
    name: str
    path: str
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/process")
def process(request: ProcessRequest) -> dict[str, object]:
    result = process_document(
        FileInfo(
            name=request.name,
            path=request.path,
            content_type=request.content_type,
        )
    )
    return {
        "document_type": result.document_type,
        "success": result.success,
        "parsed_data": result.parsed_data,
        "messages": result.messages,
    }
