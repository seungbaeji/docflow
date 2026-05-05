from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from docflow_agent.ports.llm import DocumentLlmPort
from docflow_agent.types.value.chat import ChatTurn


@dataclass(frozen=True)
class ChatUsecase:
    llm_gateway: DocumentLlmPort

    def respond(
        self,
        message: str,
        system_prompt: str | None = None,
        history: Sequence[ChatTurn] | None = None,
    ) -> str:
        return self.llm_gateway.chat(
            message=message,
            system_prompt=system_prompt,
            history=history,
        )
