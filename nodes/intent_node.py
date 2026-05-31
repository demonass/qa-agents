from schemas.state import AgentState
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import os
from typing import Optional
from tools.cache_tools import get_cached_response, set_cached_response

_TOKENIZER: Optional[AutoTokenizer] = None
_MODEL: Optional[AutoModel] = None

INTENT_CATEGORIES = {
    "CHAT": [
        "Hello, how are you?",
        "Good morning, what can you do?",
        "Nice to meet you",
        "Greetings or casual talk"
    ],
    "TEST_CASE": [
        "Write test cases for login functionality",
        "Design test scenarios for payment",
        "Create test cases for user registration",
        "Generate detailed test cases for this feature"
    ],
    "TEST_PLAN": [
        "Generate a test plan for the API",
        "Create a testing strategy document",
        "Write test scope and schedule",
        "Design overall test approach"
    ],
    "CODE_ANALYSIS": [
        "Analyze this codebase",
        "Review the code structure",
        "Check code quality and issues",
        "Examine project architecture"
    ],
    "RAG_QA": [
        "What is the architecture described in the docs?",
        "Explain how authentication works",
        "How do I configure the database?",
        "What does the documentation say about...",
        "Questions needing document knowledge"
    ],
    "RUN_TESTS": [
        "Run pytest on the tests directory",
        "Execute the test suite",
        "Run all unit tests",
        "Execute tests and show results"
    ]
}


def get_model():
    global _TOKENIZER, _MODEL
    if _TOKENIZER is None or _MODEL is None:
        model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'all-MiniLM-L6-v2')
        _TOKENIZER = AutoTokenizer.from_pretrained(model_path)
        _MODEL = AutoModel.from_pretrained(model_path)
        _MODEL.eval()
    return _TOKENIZER, _MODEL


def encode(text: str) -> np.ndarray:
    tokenizer, model = get_model()
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)

    embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
    return embeddings.flatten()


def compute_intent(user_input: str) -> str:
    user_embedding = encode(user_input)

    best_intent = "CHAT"
    best_score = -1.0

    for intent, examples in INTENT_CATEGORIES.items():
        example_embeddings = np.array([encode(example) for example in examples])
        similarities = np.dot(example_embeddings, user_embedding) / (
            np.linalg.norm(example_embeddings, axis=1) * np.linalg.norm(user_embedding)
        )
        max_similarity = float(np.max(similarities))

        if max_similarity > best_score:
            best_score = max_similarity
            best_intent = intent

    print(f"🎯 Intent: {best_intent} (similarity: {best_score:.3f})")
    return best_intent


def intent_node(state: AgentState) -> AgentState:
    print("\n--- 🔍 [Receptionist] Analyzing intent... ---")

    user_input = state.get('user_input', '')

    cached_intent = get_cached_response("intent", user_input)
    if cached_intent:
        print(f"⚡ Cache hit! Using cached intent: {cached_intent}")
        return {"intent_type": cached_intent, "messages": state.get('messages', [])}

    intent = compute_intent(user_input)

    set_cached_response("intent", user_input, intent)

    return {"intent_type": intent, "messages": state.get('messages', [])}