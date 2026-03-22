from langchain_core.tools import tool

from docflow_agent.types.source import SourceRef
from docflow_agent.usecases.process_source import process_source


@tool
def process_source_tool(
    name: str,
    location: str,
    content_type: str,
    source_system: str = "ecm",
) -> dict[str, object]:
    """Process a source through the usecase."""
    result = process_source(
        SourceRef(
            name=name,
            location=location,
            content_type=content_type,
            source_system=source_system,
        )
    )
    return {
        "source_kind": result.source_kind,
        "category": result.category,
        "success": result.success,
        "unit_count": result.unit_count,
        "bundle_data": result.bundle_data,
        "messages": result.messages,
    }
