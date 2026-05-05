from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentAgentTool:
    name: str
    description: str
    invoke: Callable[[dict[str, object], str], dict[str, object]]


@dataclass(frozen=True)
class DocumentAgentToolTrace:
    tool_name: str
    tool_input_summary: str
    tool_output_summary: str


@dataclass(frozen=True)
class DocumentAgentTrace:
    prompt: str
    tool_calls: list[DocumentAgentToolTrace] = field(default_factory=list)
    final_answer: str | None = None


@dataclass(frozen=True)
class DocumentAgentResult:
    answer: str
    trace: DocumentAgentTrace
