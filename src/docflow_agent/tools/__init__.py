"""Tool layer entrypoints for agent-style interactions.

Tools expose a small, explicit action surface to the agent runtime.
They consume prepared context from `workflow` and should not own session
selection or state transitions.
"""

from docflow_agent.tools.document import (
    DOCUMENT_AGENT_TOOLS,
    answer_about_current_document,
    get_current_document,
    parse_current_document,
    summarize_current_document,
)
from docflow_agent.types.value.document_agent import DocumentAgentToolContext

__all__ = [
    "DOCUMENT_AGENT_TOOLS",
    "DocumentAgentToolContext",
    "answer_about_current_document",
    "get_current_document",
    "parse_current_document",
    "summarize_current_document",
]
