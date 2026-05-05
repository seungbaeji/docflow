from docflow_agent.config.prompt import DEFAULT_CHAT_SYSTEM_PROMPT
from docflow_agent.outbound.testing.chat_history import InMemoryChatHistoryStore
from docflow_agent.outbound.testing.llm import StubDocumentLlmGateway
from docflow_agent.types.value.chat import ChatTurn
from docflow_agent.usecases.chat import ChatUsecase


def test_chat_usecase_stores_history_by_session() -> None:
    llm_gateway = StubDocumentLlmGateway(chat_response="hello back")
    history_store = InMemoryChatHistoryStore()
    usecase = ChatUsecase(
        llm_gateway=llm_gateway,
        chat_history_store=history_store,
        system_prompt=DEFAULT_CHAT_SYSTEM_PROMPT,
    )

    first_reply = usecase.respond(message="hello", session_id="session-001")
    second_reply = usecase.respond(message="next", session_id="session-001")

    assert first_reply == "hello back"
    assert second_reply == "hello back"
    assert llm_gateway.chatted_messages == [
        ("hello", DEFAULT_CHAT_SYSTEM_PROMPT, []),
        (
            "next",
            DEFAULT_CHAT_SYSTEM_PROMPT,
            [
                ChatTurn(role="user", content="hello"),
                ChatTurn(role="assistant", content="hello back"),
            ],
        ),
    ]
