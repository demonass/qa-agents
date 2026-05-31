import os
from datetime import datetime


def save_test_plan(content: str, filename_prefix: str) -> str:
    """
    Save generated test plan to a markdown file with timestamp.

    Args:
        content: The test plan content to save
        filename_prefix: Prefix for the filename (usually from user input)

    Returns:
        Absolute path to the saved file, or error message if failed
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join([c for c in filename_prefix[:10] if c.isalnum() or c in ['_', '-']])
        if not safe_name:
            safe_name = "TestPlan"

        filename = f"{safe_name}_{timestamp}.md"
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return os.path.abspath(filepath)
    except Exception as e:
        return f"Failed to save file: {e}"
