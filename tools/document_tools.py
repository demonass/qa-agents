from langchain_core.tools import tool
import os


@tool
def load_document(file_path: str) -> str:
    """
    Load content from various document formats.
    
    Args:
        file_path: Path to the document file (.txt, .md, .doc, .docx, .pdf)
    
    Returns:
        Content of the file as string, or error message if failed
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ('.txt', '.md'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == '.docx':
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        
        elif ext == '.doc':
            return _read_doc_file(file_path)
        
        elif ext == '.pdf':
            return _read_pdf_file(file_path)
        
        else:
            return f"Unsupported file format: {ext}. Supported formats: .txt, .md, .doc, .docx, .pdf"
    
    except Exception as e:
        return f"Failed to read file: {str(e)}"


def _read_doc_file(file_path: str) -> str:
    """Read .doc (Microsoft Word 97-2003) files."""
    try:
        import subprocess
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            subprocess.run(
                ['catdoc', file_path, '-o', tmp_path],
                check=True,
                capture_output=True
            )
            with open(tmp_path, 'r', encoding='utf-8') as f:
                return f.read()
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return f"Failed to read .doc file. Please install 'catdoc' or convert to .docx: {str(e)}"


def _read_pdf_file(file_path: str) -> str:
    """Read PDF files using pdfplumber for better text extraction."""
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n\n'
            return text.strip()
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n\n'
            return text.strip()
        except Exception as e:
            return f"Failed to read PDF: {str(e)}"


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
