"""
Platform Base — abstract base class for job platform integrations.

Each platform (LinkedIn, Naukri, Indeed, etc.) inherits from this
base and implements platform-specific search and scraping logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.services.session_manager import SessionManager


class PlatformBase(ABC):
    """Abstract base for job platform integrations."""

    PLATFORM_NAME: str = "base"
    LOGIN_URL: str = ""
    SEARCH_URL: str = ""
    REQUIRES_AUTH: bool = False

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self._session = session_manager or SessionManager()

    @abstractmethod
    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        experience_level: str | None = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for jobs on this platform.

        Returns:
            List of job result dicts with at minimum:
            {title, company, location, url, posted_date}
        """
        ...

    @abstractmethod
    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        """
        Get the full job description from a URL.

        Returns:
            Full job details dict
        """
        ...

    async def ensure_session(self, headless: bool = True) -> Any:
        """Ensure an active session exists, starting one if needed."""
        if self._session.has_session(self.PLATFORM_NAME):
            return await self._session.start(self.PLATFORM_NAME, headless=headless)

        if self.REQUIRES_AUTH:
            return await self._session.login_prompt(self.PLATFORM_NAME, self.LOGIN_URL)

        return await self._session.start(self.PLATFORM_NAME, headless=headless)

    async def save_session(self) -> str:
        """Save the current session."""
        return await self._session.save_session(self.PLATFORM_NAME)

    async def close(self) -> None:
        """Close the session."""
        await self._session.close()

    def _build_search_url(self, query: str, location: str | None = None) -> str:
        """Build a search URL — override in subclasses."""
        return self.SEARCH_URL.format(query=query, location=location or "")
