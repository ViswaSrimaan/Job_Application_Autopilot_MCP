"""
LinkedIn Platform — job search and scraping via Playwright.

Requires authentication (manual login with cookie persistence).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

from src.platforms.base import PlatformBase

logger = logging.getLogger(__name__)


class LinkedInPlatform(PlatformBase):
    """LinkedIn job search platform integration."""

    PLATFORM_NAME = "linkedin"
    LOGIN_URL = "https://www.linkedin.com/login"
    SEARCH_URL = "https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"
    REQUIRES_AUTH = True

    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
        experience_level: str | None = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search LinkedIn for jobs."""
        page = await self.ensure_session()
        if isinstance(page, dict) and page.get("status") == "waiting_for_login":
            return [page]

        url = self._build_search_url(query, location)
        if experience_level:
            level_map = {
                "entry": "2", "mid": "3,4", "senior": "4,5", "lead": "5,6",
            }
            level_param = level_map.get(experience_level.lower())
            if level_param:
                url += f"&f_E={level_param}"

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Extract job cards
        jobs = []
        cards = await page.query_selector_all(".job-card-container, .jobs-search-results__list-item")

        for card in cards[:max_results]:
            try:
                title_el = await card.query_selector(".job-card-list__title, .job-card-container__link")
                company_el = await card.query_selector(".job-card-container__primary-description, .artdeco-entity-lockup__subtitle")
                location_el = await card.query_selector(".job-card-container__metadata-wrapper, .artdeco-entity-lockup__caption")
                link_el = await card.query_selector("a[href*='/jobs/view/']")

                title = await title_el.inner_text() if title_el else "Unknown"
                company = await company_el.inner_text() if company_el else "Unknown"
                loc = await location_el.inner_text() if location_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": loc.strip(),
                    "url": f"https://www.linkedin.com{href}" if href and not href.startswith("http") else href,
                    "platform": self.PLATFORM_NAME,
                })
            except Exception as e:
                logger.warning("Failed to parse LinkedIn job card: %s", e)
                continue

        return jobs

    async def get_job_details(self, job_url: str) -> dict[str, Any]:
        """Get full job details from a LinkedIn job URL."""
        page = await self.ensure_session()
        if isinstance(page, dict):
            return page

        await page.goto(job_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        try:
            desc_el = await page.query_selector(".jobs-description__content, .show-more-less-html__markup")
            description = await desc_el.inner_text() if desc_el else ""

            title_el = await page.query_selector(".job-details-jobs-unified-top-card__job-title, h1")
            title = await title_el.inner_text() if title_el else ""

            company_el = await page.query_selector(".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name")
            company = await company_el.inner_text() if company_el else ""

            return {
                "title": title.strip(),
                "company": company.strip(),
                "description": description.strip(),
                "url": job_url,
                "platform": self.PLATFORM_NAME,
            }
        except Exception as e:
            logger.warning("Failed to scrape LinkedIn job details for %s: %s", job_url, e)
            return {"error": str(e), "url": job_url, "platform": self.PLATFORM_NAME}

    def _build_search_url(self, query: str, location: str | None = None) -> str:
        """Build LinkedIn search URL."""
        encoded_query = quote_plus(query)
        encoded_location = quote_plus(location) if location else ""
        return f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}"
