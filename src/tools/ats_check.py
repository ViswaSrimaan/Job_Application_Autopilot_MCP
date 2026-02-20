"""
MCP Tool: ats_check — run a full ATS compatibility check on a resume.
"""

from __future__ import annotations

from src.agents.ats_checker import ATSCheckerAgent
from src.services.llm import LLMService


async def ats_check(
    resume_data: dict,
    job_text: str,
    job_title: str = "Unknown Role",
    company: str = "Unknown Company",
) -> dict:
    """
    Run a full ATS compatibility check on a resume against a job description.

    Performs 3-layer analysis:
    - Layer 1: Formatting & structure (20 pts)
    - Layer 2: Keyword matching (60 pts)
    - Layer 3: Data integrity (20 pts)

    Args:
        resume_data: Parsed resume from parse_resume tool
        job_text: Raw job description text
        job_title: Job title for the report header
        company: Company name for the report header

    Returns:
        ATS report with overall score, per-layer breakdown, and recommendations
    """
    llm = LLMService()
    checker = ATSCheckerAgent(llm)
    return checker.check(resume_data, job_text, job_title, company)
