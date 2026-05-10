from langchain_core.tools import tool


@tool
def load_document(file_path: str) -> str:
    """
    Load content from a text or markdown file.
    
    Args:
        file_path: Path to the document file (.txt or .md)
    
    Returns:
        Content of the file as string, or error message if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Failed to read file: {e}"


def get_lang_instruction(language: str) -> str:
    """
    Get language instruction prompt based on selected language.
    
    Args:
        language: User's selected language (e.g., '中文', 'English')
    
    Returns:
        Language instruction string for LLM prompts
    """
    if "中文" in language:
        return "You must always respond in Simplified Chinese."
    else:
        return "You must always respond in English."
