from collections import deque

from docflow_agent.ports.queue import WorkflowQueuePort
from docflow_agent.types.boundary.external import QueueMessage


class InMemoryWorkflowQueue(WorkflowQueuePort):
    def __init__(self) -> None:
        self.messages: deque[QueueMessage] = deque()
        self.acknowledged_ids: set[str] = set()

    def enqueue(self, message: QueueMessage) -> None:
        self.messages.append(message)

    def dequeue(self) -> QueueMessage | None:
        if not self.messages:
            return None
        return self.messages.popleft()

    def ack(self, message_id: str) -> None:
        self.acknowledged_ids.add(message_id)
