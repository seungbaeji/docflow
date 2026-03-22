from docflow_agent.errors import MailIntegrationError
from docflow_agent.types.common import FileInfo


def fetch_mail_attachment(message_id: str) -> FileInfo:
    raise MailIntegrationError(message_id)
