from typing import TypedDict, Literal

class AgentState(TypedDict):
    user_input: str
    language: str
    intent_type: Literal['CHAT', 'TEST_CASE', 'TEST_PLAN', 'CODE_ANALYSIS', 'RAG_QA', 'RUN_TESTS']
    template_path: str
    template_content: str
    requirement: str
    document_content: str
    output_content: str
    iteration: int
    code_analysis: str
    rag_context: str
    use_rag: bool
    test_path: str
    test_framework: str
    test_results: str