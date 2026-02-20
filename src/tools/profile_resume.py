"""
MCP Tool: profile_resume — extract a professional profile from a parsed resume.
"""

from __future__ import annotations

from src.agents.resume_profiler import ResumeProfiler
from src.services.llm import LLMService


async def profile_resume(resume_data: dict) -> dict:
    """
    Extract a professional profile from a parsed resume.

    Analyses the resume to identify skills, experience level,
    seniority, best-fit roles, and search keywords.

    Args:
        resume_data: Output from parse_resume tool

    Returns:
        Professional profile with skills, experience, and role recommendations
    """
    llm = LLMService()
    profiler = ResumeProfiler(llm)
    return profiler.profile(resume_data)
