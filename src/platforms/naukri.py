"""
Naukri Platform — job search and scraping for the Indian market.

Uses Playwright for session managment and scraping.
"""

from __future__ import annotations

import logging
from typing import Any

from src.platforms.base import PlatformBase

logger = logging.getLogger(__name__)


class NaukriPlatform(PlatformBase):
    """Naukri.com job search platform integration."""

    PLATFORM_NAME = "naukri"
    LOGIN_URL = "https://www.naukri.com/nlogin/login"
    SEARCH_URL = "https://www.naukri.com/{query}-jobs"
    REQUIRES_AUTH = True

    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        experience_level: str | None = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Naukri for jobs."""
        page = await self.ensure_session()
        if isinstance(page, dict) and page.get("status") == "waiting_for_login":
            return [page]

        url = self._build_search_url(query, location)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        jobs = []
        cards = await page.query_selector_all(".srp-jobtuple-wrapper, .jobTupleHeader, article.jobTuple")

        for card in cards[:max_results]:
            try:
                title_el = await card.query_selector(".title, .row1 a.title")
                company_el = await card.query_selector(".comp-name, .subTitle a")
                location_el = await card.query_selector(".loc, .locWdth, .location")
                link_el = await card.query_selector("a.title, a[href*='/job-listings']")

                title = await title_el.inner_text() if title_el else "Unknown"
                company = await company_el.inner_text() if company_el else "Unknown"
                loc = await location_el.inner_text() if location_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": loc.strip(),
                    "url": href,
                    "platform": self.PLATFORM_NAME,
                })
            except Exception as e:
                logger.warning("Failed to parse Naukri job card: %s", e)
                continue

        return jobs

    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        """Get full job details from a Naukri job URL."""
        page = await self.ensure_session()
        if isinstance(page, dict):
            return page

        await page.goto(job_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        try:
            desc_el = await page.query_selector(".job-desc, .dang-inner-html, .jd-container")
            description = await desc_el.inner_text() if desc_el else ""

            title_el = await page.query_selector(".jd-header-title, h1.jd-title")
            title = await title_el.inner_text() if title_el else ""

            company_el = await page.query_selector(".jd-header-comp-name, .comp-name a")
            company = await company_el.inner_text() if company_el else ""

            return {
                "title": title.strip(),
                "company": company.strip(),
                "description": description.strip(),
                "url": job_url,
                "platform": self.PLATFORM_NAME,
            }
        except Exception as e:
            logger.warning("Failed to scrape Naukri job details for %s: %s", job_url, e)
            return {"error": str(e), "url": job_url, "platform": self.PLATFORM_NAME}

    def _build_search_url(self, query: str, location: str | None = None) -> str:
        """Build Naukri search URL."""
        encoded_query = query.lower().replace(" ", "-")
        url = f"https://www.naukri.com/{encoded_query}-jobs"
        if location:
            url += f"-in-{location.lower().replace(' ', '-')}"
        return url
