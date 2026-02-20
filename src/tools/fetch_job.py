"""
MCP Tool: fetch_job — fetch and parse a job description from URL or text.
"""

from __future__ import annotations

from src.agents.job_fetcher import JobFetcherAgent
from src.services.llm import LLMService


async def fetch_job(url: str | None = None, text: str | None = None, title: str | None = None) -> dict:
    """
    Fetch and parse a job description from a URL or pasted text.

    Extracts the job title, company, requirements, responsibilities,
    and benefits into structured JSON.

    Args:
        url: URL of the job posting (use this OR text, not both)
        text: Pasted job description text
        title: Optional job title hint

    Returns:
        Structured job data with title, company, requirements, etc.
    """
    llm = LLMService()
    fetcher = JobFetcherAgent(llm)

    if url:
        return await fetcher.fetch_from_url(url)
    elif text:
        return fetcher.parse_from_text(text, title)
    else:
        return {"error": "Provide either a URL or pasted job description text"}
