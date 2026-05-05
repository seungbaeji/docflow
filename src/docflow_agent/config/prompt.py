"""Central prompt configuration."""

DEFAULT_CHAT_SYSTEM_PROMPT = (
    "You are a concise document-processing assistant. "
    "Answer clearly, keep the response practical, and say when information is missing."
)


def get_chat_system_prompt() -> str:
    return DEFAULT_CHAT_SYSTEM_PROMPT
