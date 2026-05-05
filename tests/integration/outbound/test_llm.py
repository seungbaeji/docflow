import sys
import types

import pytest
from pydantic import SecretStr

from docflow_agent.errors import (
    LlmQuotaExceededError,
    LlmRequestError,
    MissingLlmApiKeyError,
    MissingLlmDependencyError,
    UnsupportedLlmProviderError,
)
from docflow_agent.outbound.external.llm import (
    ExternalDocumentLlmGateway,
    LlmClient,
    ask_document_question,
    build_llm_client,
    chat_text,
    summarize_document,
)
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.settings import ApiSettings, AppSettings, LlmSettings, Settings
from docflow_agent.types.value.chat import ChatTurn


def _settings_without_env(**overrides: object) -> Settings:
    base_settings = Settings.model_construct(
        app=AppSettings(),
        api=ApiSettings(),
        llm=LlmSettings(),
    )
    if not overrides:
        return base_settings
    return Settings.model_validate(base_settings.model_dump() | overrides)


class StubChatModel:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def invoke(self, _: object) -> object:
        class Response:
            def __init__(self, content: str) -> None:
                self.content = content

        return Response(self.response_text)


class FailingChatModel:
    def invoke(self, _: object) -> object:
        raise RuntimeError("quota exhausted")


class RateLimitedChatModel:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, _: object) -> object:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("RESOURCE_EXHAUSTED. Please retry in 0s.")

        class Response:
            def __init__(self, content: str) -> None:
                self.content = content

        return Response("recovered")


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


def test_external_document_llm_gateway_delegates_to_client() -> None:
    gateway = ExternalDocumentLlmGateway(
        client=LlmClient(chat_model=StubChatModel("gateway summary"))  # type: ignore[arg-type]
    )

    assert gateway.summarize_document({"amount": 1000}) == "gateway summary"
    assert gateway.chat("hello") == "gateway summary"


def test_chat_text_uses_client_output() -> None:
    answer = chat_text(
        message="hello",
        system_prompt="You are concise.",
        history=[ChatTurn(role="user", content="first"), ChatTurn(role="assistant", content="reply")],
        client=LlmClient(chat_model=StubChatModel("chat reply")),  # type: ignore[arg-type]
    )

    assert answer == "chat reply"


def test_chat_text_wraps_provider_failure() -> None:
    with pytest.raises(
        LlmQuotaExceededError,
        match="LLM request failed for provider=gemini: quota exhausted",
    ):
        chat_text(
            message="hello",
            client=LlmClient(
                chat_model=FailingChatModel(),  # type: ignore[arg-type]
                provider="gemini",
            ),
        )


def test_chat_text_retries_on_rate_limit() -> None:
    model = RateLimitedChatModel()

    answer = chat_text(
        message="hello",
        client=LlmClient(
            chat_model=model,  # type: ignore[arg-type]
            provider="gemini",
            max_retries=1,
            retry_backoff_seconds=0.0,
            retry_backoff_multiplier=1.0,
            retry_on_rate_limit=True,
        ),
    )

    assert answer == "recovered"
    assert model.calls == 2


def test_stub_document_llm_gateway_tracks_requests() -> None:
    gateway = StubDocumentLlmGateway(
        chat_response="chat",
        summary_response="summary",
        answer_response="answer",
    )

    assert gateway.chat("Hello", system_prompt="You are helpful.") == "chat"
    assert gateway.summarize_document({"document_id": "doc-001"}) == "summary"
    assert gateway.ask_document_question("What is this?", {"document_id": "doc-001"}) == "answer"
    assert gateway.chatted_messages == [("Hello", "You are helpful.", [])]
    assert gateway.summarized_payloads == [{"document_id": "doc-001"}]
    assert gateway.asked_questions == [("What is this?", {"document_id": "doc-001"})]


def test_settings_defaults_stub_provider() -> None:
    settings = _settings_without_env()

    assert settings.llm.provider == "stub"
    assert settings.llm.temperature == 0.0
    assert settings.llm.retry_backoff_seconds == 1.0
    assert settings.llm.retry_backoff_multiplier == 2.0
    assert settings.llm.retry_on_rate_limit is True
    assert settings.api.port == 8000
    assert settings.app.env == "local"


def test_settings_wraps_llm_api_key_as_secret() -> None:
    settings = _settings_without_env(llm={"api_key": "top-secret"})

    assert isinstance(settings.llm.api_key, SecretStr)
    assert settings.llm.api_key.get_secret_value() == "top-secret"


def test_settings_resolves_provider_specific_api_key() -> None:
    settings = _settings_without_env(llm={"provider": "gemini", "api_key": "gemini-secret"})

    resolved_key = settings.get_llm_api_key()

    assert resolved_key is not None
    assert resolved_key.get_secret_value() == "gemini-secret"


def test_settings_supports_nested_models() -> None:
    settings = Settings.model_validate(
        _settings_without_env().model_dump() | {
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
        build_llm_client(_settings_without_env(llm={"provider": "gemini", "api_key": None}))


def test_build_llm_client_raises_for_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = __import__("importlib").import_module

    def fake_import_module(name: str) -> object:
        if name == "langchain_google_genai":
            raise ImportError("missing dependency")
        return original_import_module(name)

    monkeypatch.setattr("docflow_agent.outbound.external.llm.import_module", fake_import_module)

    with pytest.raises(
        MissingLlmDependencyError,
        match="LLM provider 'gemini' requires optional dependency 'langchain-google-genai'",
    ):
        build_llm_client(
            _settings_without_env(llm={"provider": "gemini", "api_key": "gemini-secret"})
        )


def test_build_llm_client_supports_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}

    class FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    fake_module = types.SimpleNamespace(ChatGoogleGenerativeAI=FakeChatGoogleGenerativeAI)
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_module)

    client = build_llm_client(
        _settings_without_env(
            llm={
                "provider": "gemini",
                "model": "gemini-2.0-flash",
                "api_key": "gemini-secret",
            }
        )
    )

    assert isinstance(client, LlmClient)
    assert captured_kwargs["model"] == "gemini-2.0-flash"
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
        _settings_without_env(
            llm={
                "provider": "openai",
                "api_key": "openai-secret",
                "base_url": "https://example.test/v1",
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
        app=_settings_without_env().app,
        api=_settings_without_env().api,
        llm=_settings_without_env().llm.model_construct(provider="invalid"),
    )

    with pytest.raises(UnsupportedLlmProviderError, match="Unsupported LLM provider: invalid"):
        build_llm_client(invalid_settings)
