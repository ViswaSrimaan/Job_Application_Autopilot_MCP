"""
Job Fetcher Agent — scrapes and parses job descriptions from URLs or text.

Uses the generic scraper for URL fetching, then structures the job
description into a clean, standardised format.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from src.services.llm import LLMService
from src.services.scraper import Scraper


JD_EXTRACTION_PROMPT = """You are a job description parser. Extract structured data from this job posting.
Respond ONLY with valid JSON matching this schema:

{
    "title": "Job title",
    "company": "Company name",
    "location": "City, State/Country (Remote/Hybrid/On-site)",
    "salary_range": "₹18-25 LPA or null if not mentioned",
    "experience_required": "3+ years or null",
    "employment_type": "Full-time/Part-time/Contract/Internship",
    "posted_date": "ISO date or null if not found",
    "requirements": {
        "must_have": ["Python", "FastAPI", "3+ years backend"],
        "nice_to_have": ["Kubernetes", "AWS"]
    },
    "responsibilities": ["Design and build APIs", "Lead a team of 3"],
    "benefits": ["Health insurance", "Stock options"],
    "description_summary": "2-3 sentence summary of the role",
    "full_description": "Full job description text"
}

Be precise. Only fill fields with data actually present in the posting."""


class JobFetcherAgent:
    """Fetches and parses job descriptions from URLs or raw text."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._scraper = Scraper()
        self._llm = llm or LLMService()

    async def fetch_from_url(self, url: str) -> dict[str, Any]:
        """
        Fetch a job posting from a URL and extract structured data.

        Returns:
            Structured job data dict with an assigned job_id
        """
        # Fetch the page
        page = await self._scraper.fetch(url)

        if page["error"]:
            return {
                "error": page["error"],
                "url": url,
                "job_id": None,
            }

        # Try to extract job-specific content from HTML
        job_content = Scraper.extract_job_content(page["html"])

        # Use the best available text
        description_text = job_content.get("description") or page["text"]

        # Generate a job ID
        job_id = self._generate_job_id(url)

        # Structure the job data
        return self._structure_job(
            text=description_text,
            url=url,
            job_id=job_id,
            title_hint=job_content.get("title") or page.get("title"),
            company_hint=job_content.get("company"),
        )

    def fetch_from_url_sync(self, url: str) -> dict[str, Any]:
        """Synchronous version of fetch_from_url()."""
        page = self._scraper.fetch_sync(url)

        if page["error"]:
            return {
                "error": page["error"],
                "url": url,
                "job_id": None,
            }

        job_content = Scraper.extract_job_content(page["html"])
        description_text = job_content.get("description") or page["text"]
        job_id = self._generate_job_id(url)

        return self._structure_job(
            text=description_text,
            url=url,
            job_id=job_id,
            title_hint=job_content.get("title") or page.get("title"),
            company_hint=job_content.get("company"),
        )

    def parse_from_text(self, text: str, title: str | None = None) -> dict[str, Any]:
        """
        Parse a pasted job description text.

        Args:
            text: Raw job description text
            title: Optional job title hint

        Returns:
            Structured job data dict
        """
        job_id = self._generate_job_id(text[:100])

        return self._structure_job(
            text=text,
            url=None,
            job_id=job_id,
            title_hint=title,
            company_hint=None,
        )

    def _structure_job(
        self,
        text: str,
        url: str | None,
        job_id: str,
        title_hint: str | None,
        company_hint: str | None,
    ) -> dict[str, Any]:
        """Use LLM to extract structured job data from text."""
        prompt = f"""Parse this job posting and extract structured data.

Job posting text:
---
{text[:5000]}
---

{f'Title hint: {title_hint}' if title_hint else ''}
{f'Company hint: {company_hint}' if company_hint else ''}

Extract the structured data as JSON following the schema in your instructions."""

        result = self._llm.generate_structured(
            prompt=prompt,
            system=JD_EXTRACTION_PROMPT,
            temperature=0.1,
        )

        # In MCP mode, return the prompt for the host AI
        if result.get("requires_host_ai"):
            return {
                "job_id": job_id,
                "url": url,
                "status": "mcp_mode",
                "raw_text": text[:5000],
                "prompt": result["mcp_prompt"],
                "title_hint": title_hint,
                "company_hint": company_hint,
                "instruction": "The host AI should parse this job description into structured JSON.",
            }

        # Add metadata
        result["job_id"] = job_id
        result["url"] = url
        result["fetched_at"] = datetime.now().isoformat()
        result["raw_text"] = text[:5000]

        return result

    @staticmethod
    def _generate_job_id(seed: str) -> str:
        """Generate a short unique job ID using SHA-256."""
        hash_val = hashlib.sha256(seed.encode()).hexdigest()[:8]
        return f"job_{hash_val}"
