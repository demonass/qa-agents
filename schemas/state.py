from typing import TypedDict, Literal

class AgentState(TypedDict):
    user_input: str
    language: str
    intent_type: Literal['CHAT', 'TEST_CASE', 'TEST_PLAN']
    template_path: str
    template_content: str
    requirement: str
    document_content: str
    output_content: str
    iteration: int