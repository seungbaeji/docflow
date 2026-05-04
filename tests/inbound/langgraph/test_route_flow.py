from docflow_agent.inbound.langgraph.routes import route_flow


def test_route_flow_document_process_for_document_prompt() -> None:
    state = {"user_input": "엑셀 문서를 분석해줘"}
    assert route_flow(state) == "document_process"


def test_route_flow_document_to_mail_for_document_and_mail_prompt() -> None:
    state = {"user_input": "엑셀에서 미정산 건을 찾아 메일로 보내줘"}
    assert route_flow(state) == "document_to_mail"


def test_route_flow_unknown_for_unrelated_prompt() -> None:
    state = {"user_input": "점심 메뉴를 추천해줘"}
    assert route_flow(state) == "unknown"

