from dataclasses import dataclass, field


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
