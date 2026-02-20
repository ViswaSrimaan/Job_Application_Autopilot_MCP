"""
Platform Agent — multi-platform job search orchestrator.

Routes queries to the appropriate platform(s) and aggregates results.
"""

from __future__ import annotations

from typing import Any

from src.platforms.base import PlatformBase
from src.platforms.linkedin import LinkedInPlatform
from src.platforms.naukri import NaukriPlatform
from src.platforms.others import (
    CutshortPlatform,
    FounditPlatform,
    IndeedPlatform,
    WellfoundPlatform,
)
from src.services.session_manager import SessionManager


PLATFORM_REGISTRY: dict[str, type[PlatformBase]] = {
    "linkedin": LinkedInPlatform,
    "naukri": NaukriPlatform,
    "indeed": IndeedPlatform,
}

# Not yet implemented — excluded from default search to avoid noisy errors
COMING_SOON_PLATFORMS: dict[str, type[PlatformBase]] = {
    "cutshort": CutshortPlatform,
    "foundit": FounditPlatform,
    "wellfound": WellfoundPlatform,
}


class PlatformAgent:
    """Orchestrates job searches across multiple platforms."""

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self._session = session_manager or SessionManager()
        self._platforms: dict[str, PlatformBase] = {}

    def _get_platform(self, name: str) -> PlatformBase:
        """Get or create a platform instance."""
        if name not in self._platforms:
            platform_cls = PLATFORM_REGISTRY.get(name)
            if not platform_cls:
                raise ValueError(
                    f"Unknown platform '{name}'. Available: {', '.join(PLATFORM_REGISTRY.keys())}"
                )
            self._platforms[name] = platform_cls(self._session)
        return self._platforms[name]

    async def search(
        self,
        query: str,
        platforms: list[str] | None = None,
        location: str | None = None,
        experience_level: str | None = None,
        max_per_platform: int = 10,
    ) -> dict[str, Any]:
        """
        Search for jobs across multiple platforms.

        Args:
            query: Job search query
            platforms: List of platform names (default: all available)
            location: Location filter
            experience_level: Experience level filter
            max_per_platform: Max results per platform

        Returns:
            dict with aggregated results
        """
        target_platforms = platforms or list(PLATFORM_REGISTRY.keys())
        all_results: dict[str, list[dict]] = {}
        errors: dict[str, str] = {}

        for platform_name in target_platforms:
            try:
                platform = self._get_platform(platform_name)
                results = await platform.search_jobs(
                    query=query,
                    location=location,
                    experience_level=experience_level,
                    max_results=max_per_platform,
                )
                all_results[platform_name] = results
            except Exception as e:
                errors[platform_name] = str(e)
                all_results[platform_name] = []

        # Aggregate
        total_jobs = sum(len(jobs) for jobs in all_results.values())

        return {
            "query": query,
            "location": location,
            "platforms_searched": target_platforms,
            "total_results": total_jobs,
            "results": all_results,
            "errors": errors,
        }

    async def get_job_details(self, platform_name: str, job_url: str) -> dict[str, Any]:
        """
        Get full job details from a specific platform.

        Args:
            platform_name: Platform to use
            job_url: Job URL to scrape

        Returns:
            Job details dict
        """
        platform = self._get_platform(platform_name)
        return await platform.get_job_details(job_url)

    async def login(self, platform_name: str) -> dict[str, Any]:
        """Open a login prompt for a platform."""
        platform = self._get_platform(platform_name)
        return await platform.ensure_session(headless=False)

    async def close_all(self) -> None:
        """Close all active platform sessions."""
        for platform in self._platforms.values():
            try:
                await platform.close()
            except Exception:
                pass
        self._platforms.clear()

    @staticmethod
    def list_platforms() -> list[dict[str, Any]]:
        """List all available platforms."""
        platforms = [
            {
                "name": name,
                "requires_auth": cls.REQUIRES_AUTH,
                "login_url": cls.LOGIN_URL,
                "status": "available",
            }
            for name, cls in PLATFORM_REGISTRY.items()
        ]
        platforms.extend(
            {
                "name": name,
                "requires_auth": cls.REQUIRES_AUTH,
                "login_url": cls.LOGIN_URL,
                "status": "coming_soon",
            }
            for name, cls in COMING_SOON_PLATFORMS.items()
        )
        return platforms
