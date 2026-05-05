from typing import Protocol

from docflow_agent.types.external import QueueMessage


class WorkflowQueuePort(Protocol):
    def enqueue(self, message: QueueMessage) -> None:
        ...

    def dequeue(self) -> QueueMessage | None:
        ...

    def ack(self, message_id: str) -> None:
        ...

