from collections import deque
from dataclasses import dataclass, field

from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.types.boundary.external import QueueMessage


@dataclass
class InMemoryWorkflowQueue(WorkflowQueuePort):
    messages: deque[QueueMessage] = field(default_factory=deque)
    acknowledged_ids: set[str] = field(default_factory=set)

    def enqueue(self, message: QueueMessage) -> None:
        self.messages.append(message)

    def dequeue(self) -> QueueMessage | None:
        if not self.messages:
            return None
        return self.messages.popleft()

    def ack(self, message_id: str) -> None:
        self.acknowledged_ids.add(message_id)
