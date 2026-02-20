"""
MCP Tool: parse_resume — parse a PDF/DOCX resume into structured JSON.
"""

from __future__ import annotations

from pathlib import Path

from src.agents.resume_parser import ResumeParserAgent

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


async def parse_resume(file_path: str) -> dict:
    """
    Parse a resume file (PDF or DOCX) into structured JSON.

    Extracts contact information, section headers, experience,
    skills, and formatting metadata using IBM Docling.

    Args:
        file_path: Absolute path to the resume file (.pdf or .docx)

    Returns:
        Structured resume data with contact info, sections, and ATS warnings
    """
    # Guard rail: resolve and validate file path
    resolved = Path(file_path).resolve()

    if not resolved.is_file():
        return {"error": f"File not found: {file_path}"}

    if resolved.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return {
            "error": f"Unsupported file type: {resolved.suffix}",
            "allowed": list(_ALLOWED_EXTENSIONS),
        }

    parser = ResumeParserAgent()
    return parser.parse(str(resolved))
