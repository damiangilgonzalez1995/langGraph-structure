from typing import TypedDict


class AgentGraphState(TypedDict):
    input: str
    input_filter: dict
    relevant_fields: str
    query: dict
    state_ok_ko: bool


state = {
    "input":"",
    "input_filter": {},
    "relevant_fields": "",
    "query": {},
    "state_ok_ko": ""

}