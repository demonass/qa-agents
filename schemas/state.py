from typing import TypedDict, Literal

class AgentState(TypedDict):
    user_input: str
    language: str
    intent_type: Literal['CHAT', 'TEST_CASE', 'TEST_PLAN', 'CODE_ANALYSIS', 'RAG_QA']
    template_path: str
    template_content: str
    requirement: str
    document_content: str
    output_content: str
    iteration: int
    code_analysis: str
    rag_context: str