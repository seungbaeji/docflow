from typing import TypedDict


class State(TypedDict, total=False):
    session_id: str
    message: str
    source_ref_id: str
