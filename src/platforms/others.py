"""
Indeed, Cutshort, Foundit, Wellfound — stub platform integrations.

These follow the same PlatformBase pattern. They are structured stubs
ready for detailed selector implementation based on the live site DOM.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

from src.platforms.base import PlatformBase

logger = logging.getLogger(__name__)


class IndeedPlatform(PlatformBase):
    """Indeed job search platform integration."""

    PLATFORM_NAME = "indeed"
    LOGIN_URL = "https://secure.indeed.com/auth"
    SEARCH_URL = "https://www.indeed.com/jobs?q={query}&l={location}"
    REQUIRES_AUTH = False

    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        experience_level: str | None = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Indeed for jobs."""
        page = await self.ensure_session()
        if isinstance(page, dict):
            return [page]

        url = f"https://www.indeed.com/jobs?q={quote_plus(query)}"
        if location:
            url += f"&l={quote_plus(location)}"

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        jobs = []
        cards = await page.query_selector_all(".job_seen_beacon, .resultContent, .tapItem")

        for card in cards[:max_results]:
            try:
                title_el = await card.query_selector("h2.jobTitle a, .jcs-JobTitle a")
                company_el = await card.query_selector("[data-testid='company-name'], .companyName")
                location_el = await card.query_selector("[data-testid='text-location'], .companyLocation")

                title = await title_el.inner_text() if title_el else "Unknown"
                href = await title_el.get_attribute("href") if title_el else ""
                company = await company_el.inner_text() if company_el else "Unknown"
                loc = await location_el.inner_text() if location_el else ""

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": loc.strip(),
                    "url": f"https://www.indeed.com{href}" if href and not href.startswith("http") else href,
                    "platform": self.PLATFORM_NAME,
                })
            except Exception as e:
                logger.warning("Failed to parse Indeed job card: %s", e)
                continue

        return jobs

    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        """Get full job details from an Indeed URL."""
        page = await self.ensure_session()
        if isinstance(page, dict):
            return page

        await page.goto(job_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        try:
            desc_el = await page.query_selector("#jobDescriptionText, .jobsearch-jobDescriptionText")
            description = await desc_el.inner_text() if desc_el else ""

            title_el = await page.query_selector("h1.jobsearch-JobInfoHeader-title, h1")
            title = await title_el.inner_text() if title_el else ""

            return {
                "title": title.strip(),
                "description": description.strip(),
                "url": job_url,
                "platform": self.PLATFORM_NAME,
            }
        except Exception as e:
            logger.warning("Failed to scrape Indeed job details for %s: %s", job_url, e)
            return {"error": str(e), "url": job_url, "platform": self.PLATFORM_NAME}


class CutshortPlatform(PlatformBase):
    """Cutshort job platform integration (stub)."""

    PLATFORM_NAME = "cutshort"
    LOGIN_URL = "https://cutshort.io/login"
    REQUIRES_AUTH = True

    async def search_jobs(self, query: str, location: str | None = None, experience_level: str | None = None, max_results: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError("Cutshort integration pending — DOM selectors to be added")

    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        raise NotImplementedError("Cutshort job details pending — DOM selectors to be added")


class FounditPlatform(PlatformBase):
    """Foundit (Monster India) platform integration (stub)."""

    PLATFORM_NAME = "foundit"
    LOGIN_URL = "https://www.foundit.in/login"
    REQUIRES_AUTH = True

    async def search_jobs(self, query: str, location: str | None = None, experience_level: str | None = None, max_results: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError("Foundit integration pending — DOM selectors to be added")

    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        raise NotImplementedError("Foundit job details pending — DOM selectors to be added")


class WellfoundPlatform(PlatformBase):
    """Wellfound (AngelList) platform integration (stub)."""

    PLATFORM_NAME = "wellfound"
    LOGIN_URL = "https://wellfound.com/login"
    REQUIRES_AUTH = True

    async def search_jobs(self, query: str, location: str | None = None, experience_level: str | None = None, max_results: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError("Wellfound integration pending — DOM selectors to be added")

    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        raise NotImplementedError("Wellfound job details pending — DOM selectors to be added")
