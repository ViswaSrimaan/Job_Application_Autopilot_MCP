"""
Resume Profiler Agent — analyses parsed resume to extract a professional profile.

Uses the LLM (in CLI mode) or returns structured prompts (in MCP mode)
to extract skills, experience level, seniority, and best-fit role titles.
"""

from __future__ import annotations

import json
from typing import Any

from src.services.llm import LLMService


# System prompt for the LLM to extract a resume profile
PROFILE_SYSTEM_PROMPT = """You are an expert recruiter and career analyst.
Analyse the given resume text and extract a structured professional profile.
Respond ONLY with valid JSON matching this exact schema:

{
    "name": "Full name of the candidate",
    "current_title": "Most recent job title",
    "experience_years": 4.5,
    "seniority_level": "one of: entry, junior, mid, senior, lead, principal, executive",
    "hard_skills": ["Python", "FastAPI", "PostgreSQL"],
    "soft_skills": ["Leadership", "Communication"],
    "domains": ["FinTech", "E-commerce"],
    "education": [
        {
            "degree": "Bachelor of Technology",
            "field": "Computer Science",
            "institution": "IIT Delhi",
            "year": 2019
        }
    ],
    "certifications": ["AWS Solutions Architect"],
    "best_fit_roles": [
        "Senior Python Developer",
        "Backend Engineer",
        "Platform Engineer"
    ],
    "search_keywords": ["python developer", "backend engineer", "fastapi"],
    "summary": "Brief 2-sentence professional summary"
}

Be precise. Only include skills actually mentioned or clearly demonstrated.
For best_fit_roles, suggest 3-5 roles the candidate would be a strong match for.
For search_keywords, suggest terms to use when searching job platforms."""


class ResumeProfiler:
    """Extracts a professional profile from a parsed resume."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()

    def profile(self, resume_data: dict[str, Any]) -> dict[str, Any]:
        """
        Analyse a parsed resume and extract a professional profile.

        Args:
            resume_data: Output from ResumeParserAgent.parse()

        Returns:
            Structured profile dict (or MCP prompt if in MCP mode)
        """
        resume_text = resume_data.get("raw_text", "")
        contact = resume_data.get("contact", {})

        prompt = f"""Analyse this resume and extract a professional profile.

Resume text:
---
{LLMService.sanitize_content(resume_text, "RESUME")}
---

Contact info already extracted:
- Name: {contact.get('name', 'Unknown')}
- Email: {contact.get('email', 'Not found')}

Extract the profile as JSON following the schema in your instructions."""

        result = self._llm.generate_structured(
            prompt=prompt,
            system=PROFILE_SYSTEM_PROMPT,
            temperature=0.2,
        )

        # In MCP mode, wrap the prompt for the host AI
        if result.get("requires_host_ai"):
            return {
                "status": "mcp_mode",
                "prompt": result["mcp_prompt"],
                "contact": contact,
                "instruction": (
                    "The host AI should process this prompt and return "
                    "a JSON profile matching the schema described above."
                ),
            }

        # Add contact info to the profile
        if not result.get("parse_error"):
            result["contact"] = contact

        return result

    def get_search_queries(self, profile: dict[str, Any]) -> list[dict[str, str]]:
        """
        Generate platform search queries from a profile.

        Returns list of {query, location_hint} dicts.
        """
        queries = []

        best_fit_roles = profile.get("best_fit_roles", [])
        search_keywords = profile.get("search_keywords", [])

        # Primary queries from best-fit roles
        for role in best_fit_roles[:3]:
            queries.append({
                "query": role,
                "type": "role_title",
            })

        # Secondary queries from search keywords
        for keyword in search_keywords[:3]:
            if keyword.lower() not in [r.lower() for r in best_fit_roles]:
                queries.append({
                    "query": keyword,
                    "type": "keyword",
                })

        # Skill-based query
        hard_skills = profile.get("hard_skills", [])
        if hard_skills:
            top_skills = " ".join(hard_skills[:4])
            queries.append({
                "query": top_skills,
                "type": "skills",
            })

        return queries
