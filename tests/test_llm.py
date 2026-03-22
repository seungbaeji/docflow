import pytest
from pydantic import SecretStr

from docflow_agent.errors import UnsupportedLlmProviderError
from docflow_agent.outbound.llm import LlmClient, ask_document_question, summarize_document
from docflow_agent.settings import Settings


class StubChatModel:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def invoke(self, _: object) -> object:
        class Response:
            def __init__(self, content: str) -> None:
                self.content = content

        return Response(self.response_text)


def test_summarize_document_uses_client_output() -> None:
    summary = summarize_document(
        {"source_kind": "excel", "category": "invoice", "amount": 1000},
        client=LlmClient(chat_model=StubChatModel("invoice summary")),  # type: ignore[arg-type]
    )

    assert summary == "invoice summary"


def test_ask_document_question_uses_client_output() -> None:
    answer = ask_document_question(
        question="What is the amount?",
        payload={"amount": 1000},
        client=LlmClient(chat_model=StubChatModel("The amount is 1000.")),  # type: ignore[arg-type]
    )

    assert answer == "The amount is 1000."


def test_settings_defaults_stub_provider() -> None:
    settings = Settings()

    assert settings.llm_provider == "stub"
    assert settings.llm_temperature == 0.0


def test_settings_wraps_llm_api_key_as_secret() -> None:
    settings = Settings.model_validate({"llm_api_key": "top-secret"})

    assert isinstance(settings.llm_api_key, SecretStr)
    assert settings.llm_api_key.get_secret_value() == "top-secret"


def test_build_llm_client_raises_for_unsupported_provider() -> None:
    from docflow_agent.outbound.llm import build_llm_client

    with pytest.raises(UnsupportedLlmProviderError, match="Unsupported LLM provider: invalid"):
        build_llm_client(Settings(llm_provider="invalid"))
