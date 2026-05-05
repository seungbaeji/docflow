from docflow_agent.outbound.testing.queue import InMemoryWorkflowQueue
from docflow_agent.types.boundary.external import QueueMessage


def test_workflow_queue_enqueues_and_dequeues_messages() -> None:
    queue = InMemoryWorkflowQueue()
    message = QueueMessage(
        message_id="msg-001",
        topic="document.process",
        payload={"source_ref_id": "source-001"},
        metadata={"flow": "document_process"},
    )

    queue.enqueue(message)

    assert queue.dequeue() == message
    assert queue.dequeue() is None


def test_workflow_queue_tracks_acknowledged_messages() -> None:
    queue = InMemoryWorkflowQueue()

    queue.ack("msg-001")

    assert "msg-001" in queue.acknowledged_ids
