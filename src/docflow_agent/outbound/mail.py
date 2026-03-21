from docflow_agent.types.common import FileInfo


def fetch_mail_attachment(message_id: str) -> FileInfo:
    raise NotImplementedError(f"Mail integration is stubbed for message_id={message_id}")
