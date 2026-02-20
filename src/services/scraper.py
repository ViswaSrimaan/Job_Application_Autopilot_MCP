"""
Generic Web Scraper — fetches and extracts text from URLs.

Uses httpx for HTTP requests and BeautifulSoup4 for HTML parsing.
Designed for scraping job descriptions from job posting URLs.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Scraper:
    """Lightweight URL scraper for job postings and web content."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 30, max_retries: int = 3) -> None:
        self._timeout = timeout
        self._max_retries = max_retries

    async def fetch(self, url: str) -> dict[str, str | None]:
        """
        Fetch a URL and extract structured content.

        Returns:
            dict with keys:
                - url: the original URL
                - title: page title
                - text: extracted text content
                - html: raw HTML (for further parsing)
                - error: error message if failed, None otherwise
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    headers=self.DEFAULT_HEADERS,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    html = response.text
                    soup = BeautifulSoup(html, "html.parser")

                    for element in soup(["script", "style", "nav", "footer", "header"]):
                        element.decompose()

                    title = soup.title.string.strip() if soup.title and soup.title.string else None
                    text = soup.get_text(separator="\n", strip=True)

                    return {
                        "url": url,
                        "title": title,
                        "text": text,
                        "html": html,
                        "error": None,
                    }

            except httpx.HTTPStatusError as e:
                return {
                    "url": url,
                    "title": None,
                    "text": None,
                    "html": None,
                    "error": f"HTTP error {e.response.status_code}: {e.response.reason_phrase}",
                }
            except httpx.RequestError as e:
                if attempt < self._max_retries:
                    wait = 2 ** (attempt - 1)
                    logger.warning("Retry %d/%d for %s after error: %s", attempt, self._max_retries, url, e)
                    await asyncio.sleep(wait)
                    continue
                return {
                    "url": url,
                    "title": None,
                    "text": None,
                    "html": None,
                    "error": f"Request failed after {self._max_retries} retries: {e}",
                }

    def fetch_sync(self, url: str) -> dict[str, str | None]:
        """Synchronous version of fetch()."""
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self._timeout,
                    headers=self.DEFAULT_HEADERS,
                    follow_redirects=True,
                ) as client:
                    response = client.get(url)
                    response.raise_for_status()

                    html = response.text
                    soup = BeautifulSoup(html, "html.parser")

                    for element in soup(["script", "style", "nav", "footer", "header"]):
                        element.decompose()

                    title = soup.title.string.strip() if soup.title and soup.title.string else None
                    text = soup.get_text(separator="\n", strip=True)

                    return {
                        "url": url,
                        "title": title,
                        "text": text,
                        "html": html,
                        "error": None,
                    }
            except httpx.HTTPStatusError as e:
                return {
                    "url": url,
                    "title": None,
                    "text": None,
                    "html": None,
                    "error": f"HTTP error {e.response.status_code}: {e.response.reason_phrase}",
                }
            except httpx.RequestError as e:
                if attempt < self._max_retries:
                    wait = 2 ** (attempt - 1)
                    logger.warning("Retry %d/%d for %s after error: %s", attempt, self._max_retries, url, e)
                    time.sleep(wait)
                    continue
                return {
                    "url": url,
                    "title": None,
                    "text": None,
                    "html": None,
                    "error": f"Request failed after {self._max_retries} retries: {e}",
                }

    @staticmethod
    def extract_job_content(html: str) -> dict[str, str | None]:
        """
        Extract job-specific content from HTML.

        Looks for common job posting patterns and structures.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Common job description selectors
        job_selectors = [
            {"class_": "job-description"},
            {"class_": "jobDescriptionContent"},
            {"class_": "description"},
            {"class_": "job-details"},
            {"id": "job-description"},
            {"id": "jobDescription"},
            {"class_": "jd-container"},
        ]

        description = None
        for selector in job_selectors:
            element = soup.find("div", **selector)
            if element:
                description = element.get_text(separator="\n", strip=True)
                break

        if not description:
            # Fallback: find the largest text block
            main = soup.find("main") or soup.find("article") or soup.find("body")
            if main:
                description = main.get_text(separator="\n", strip=True)

        # Extract job title
        title = None
        title_selectors = [
            {"class_": "job-title"},
            {"class_": "jobTitle"},
            {"class_": "title"},
        ]
        for selector in title_selectors:
            element = soup.find(["h1", "h2"], **selector)
            if element:
                title = element.get_text(strip=True)
                break

        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Extract company name
        company = None
        company_selectors = [
            {"class_": "company-name"},
            {"class_": "companyName"},
            {"class_": "company"},
        ]
        for selector in company_selectors:
            element = soup.find(["span", "a", "div"], **selector)
            if element:
                company = element.get_text(strip=True)
                break

        return {
            "title": title,
            "company": company,
            "description": description,
        }
