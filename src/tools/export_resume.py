"""
MCP Tool: export_resume — export tailored resume to DOCX format.
"""

from __future__ import annotations

from src.services.doc_exporter import DocExporter


async def export_resume(
    resume_text: str,
    contact: dict | None = None,
    sections: dict | None = None,
    filename: str | None = None,
    job_title: str | None = None,
    company: str | None = None,
    tailor_token: str | None = None,
) -> dict:
    """
    Export a resume (original or tailored) to a formatted DOCX file.

    Creates a professionally formatted Word document with proper
    margins, section headers, and consistent styling.

    Args:
        resume_text: The resume text to export
        contact: Contact info (name, email, phone)
        sections: Organised resume sections
        filename: Custom filename (auto-generated if not provided)
        job_title: Job title (for auto-naming)
        company: Company name (for auto-naming)
        tailor_token: Token from tailor_resume (required when exporting tailored content)

    Returns:
        Path to the created DOCX file
    """
    # Guard rail: validate tailor token when provided
    if tailor_token is not None:
        from src.tools.tailor_resume import validate_tailor_token

        validated_text = validate_tailor_token(tailor_token)
        if validated_text is None:
            return {
                "error": "Invalid or expired tailor token. Please re-run tailor_resume first.",
            }
        # Use the validated text (ignore whatever was passed as resume_text)
        resume_text = validated_text

    exporter = DocExporter()
    path = exporter.export(resume_text, contact, sections, filename, job_title, company)
    return {"file_path": path, "message": f"Resume exported to {path}"}
