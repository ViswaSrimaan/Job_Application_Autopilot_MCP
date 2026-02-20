"""
MCP Tool: search_jobs — search for jobs across multiple platforms.
"""

from __future__ import annotations

from src.agents.platform_agent import PlatformAgent


async def search_jobs(
    query: str,
    platforms: list[str] | None = None,
    location: str | None = None,
    experience_level: str | None = None,
    max_per_platform: int = 10,
) -> dict:
    """
    Search for jobs across multiple platforms (LinkedIn, Naukri, Indeed, etc.).

    Aggregates results from selected platforms and returns
    a unified list of job postings.

    Args:
        query: Job search query (e.g., "Senior Python Developer")
        platforms: List of platforms to search (default: all).
                   Options: linkedin, naukri, indeed, cutshort, foundit, wellfound
        location: Location filter (e.g., "Bangalore", "Remote")
        experience_level: Filter by level — "entry", "mid", "senior", "lead"
        max_per_platform: Maximum results per platform (default 10)

    Returns:
        Aggregated job search results from all platforms
    """
    agent = PlatformAgent()
    try:
        return await agent.search(
            query=query,
            platforms=platforms,
            location=location,
            experience_level=experience_level,
            max_per_platform=max_per_platform,
        )
    finally:
        await agent.close_all()
