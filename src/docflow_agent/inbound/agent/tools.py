from langchain_core.tools import tool

from docflow_agent.types.common import FileInfo
from docflow_agent.usecases.process_document import process_document


@tool
def process_document_tool(name: str, path: str, content_type: str) -> dict[str, object]:
    """Process a document through the usecase."""
    result = process_document(FileInfo(name=name, path=path, content_type=content_type))
    return {
        "document_type": result.document_type,
        "success": result.success,
        "parsed_data": result.parsed_data,
        "messages": result.messages,
    }
