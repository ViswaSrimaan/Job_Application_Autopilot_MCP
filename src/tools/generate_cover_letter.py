"""
MCP Tool: generate_cover_letter — create a personalised cover letter.
"""

from __future__ import annotations

from src.agents.cover_letter_agent import CoverLetterAgent
from src.services.llm import LLMService


async def generate_cover_letter(
    resume_data: dict,
    job_data: dict,
    profile: dict | None = None,
    tone: str = "professional",
) -> dict:
    """
    Generate a personalised cover letter for a job application.

    Creates a tailored, 400-word cover letter that highlights
    relevant achievements and matches the job requirements.

    Args:
        resume_data: Parsed resume from parse_resume tool
        job_data: Structured job from fetch_job tool
        profile: Optional resume profile from profile_resume tool
        tone: Writing tone — "professional", "warm", or "bold"

    Returns:
        Generated cover letter with word count and metadata
    """
    llm = LLMService()
    agent = CoverLetterAgent(llm)
    result = agent.generate(resume_data, job_data, profile, tone)
    result["requires_review"] = True
    return result
