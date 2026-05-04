import sys
import types

import pytest
from pydantic import SecretStr

from docflow_agent.errors import (
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedLlmProviderError,
)
from docflow_agent.outbound.llm import (
    LlmClient,
    ask_document_question,
    build_llm_client,
    summarize_document,
)
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

    assert settings.llm.provider == "stub"
    assert settings.llm.temperature == 0.0
    assert settings.api.port == 8000
    assert settings.app.env == "local"


def test_settings_wraps_llm_api_key_as_secret() -> None:
    settings = Settings.model_validate({"llm": {"api_key": "top-secret"}})

    assert isinstance(settings.llm.api_key, SecretStr)
    assert settings.llm.api_key.get_secret_value() == "top-secret"


def test_settings_resolves_provider_specific_api_key() -> None:
    settings = Settings.model_validate({"llm": {"provider": "gemini", "api_key": "gemini-secret"}})

    resolved_key = settings.get_llm_api_key()

    assert resolved_key is not None
    assert resolved_key.get_secret_value() == "gemini-secret"


def test_settings_supports_nested_models() -> None:
    settings = Settings.model_validate(
        {
            "app": {"env": "test", "debug": True},
            "api": {"port": 9000, "reload": True},
            "llm": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "base_url": "https://example.test/v1",
            },
        }
    )

    assert settings.app.env == "test"
    assert settings.app.debug is True
    assert settings.api.port == 9000
    assert settings.api.reload is True
    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4.1-mini"
    assert settings.get_llm_base_url() == "https://example.test/v1"


def test_build_llm_client_raises_for_missing_api_key() -> None:
    with pytest.raises(MissingLlmApiKeyError, match="Missing API key for LLM provider: gemini"):
        build_llm_client(Settings.model_validate({"llm": {"provider": "gemini"}}))


def test_build_llm_client_raises_for_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = __import__("importlib").import_module

    def fake_import_module(name: str) -> object:
        if name == "langchain_google_genai":
            raise ImportError("missing dependency")
        return original_import_module(name)

    monkeypatch.setattr("docflow_agent.outbound.llm.import_module", fake_import_module)

    with pytest.raises(
        MissingLlmDependencyError,
        match="LLM provider 'gemini' requires optional dependency 'langchain-google-genai'",
    ):
        build_llm_client(
            Settings.model_validate(
                {"llm": {"provider": "gemini", "api_key": "gemini-secret"}}
            )
        )


def test_build_llm_client_supports_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    fake_module = types.SimpleNamespace(ChatGoogleGenerativeAI=FakeChatGoogleGenerativeAI)
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_module)

    client = build_llm_client(
        Settings.model_validate(
            {
                "llm": {
                    "provider": "gemini",
                    "api_key": "gemini-secret",
                }
            }
        )
    )

    assert isinstance(client, LlmClient)
    assert captured_kwargs["model"] == "gpt-4o-mini"
    assert captured_kwargs["temperature"] == 0.0
    assert captured_kwargs["google_api_key"] == "gemini-secret"


def test_build_llm_client_supports_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    fake_module = types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI)
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)

    client = build_llm_client(
        Settings.model_validate(
            {
                "llm": {
                    "provider": "openai",
                    "api_key": "openai-secret",
                    "base_url": "https://example.test/v1",
                }
            }
        )
    )

    assert isinstance(client, LlmClient)
    assert captured_kwargs["api_key"] == SecretStr("openai-secret")
    assert captured_kwargs["base_url"] == "https://example.test/v1"
    assert captured_kwargs["timeout"] == 30.0
    assert captured_kwargs["max_retries"] == 2


def test_build_llm_client_raises_for_unsupported_provider() -> None:

    invalid_settings = Settings.model_construct(
        app=Settings().app,
        api=Settings().api,
        llm=Settings().llm.model_construct(provider="invalid"),
    )

    with pytest.raises(UnsupportedLlmProviderError, match="Unsupported LLM provider: invalid"):
        build_llm_client(invalid_settings)
