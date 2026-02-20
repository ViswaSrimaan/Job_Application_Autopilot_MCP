"""
JD Extractor — LLM structured output for job description analysis.

Extracts required skills, preferred skills, soft skills, experience
requirements, education requirements, and acronym expansions from
a job description using LLM structured JSON output.
"""

from __future__ import annotations

from typing import Any

from src.services.llm import LLMService


JD_EXTRACTION_SYSTEM = """You are a technical recruiter parsing a job description.
Extract ALL skills, requirements, and qualifications. Be thorough and precise.

Respond ONLY with valid JSON matching this exact schema:

{
    "required_hard_skills": ["Python", "Kafka", "Kubernetes", "gRPC"],
    "preferred_hard_skills": ["FastAPI", "Redis", "PostgreSQL"],
    "soft_skills": ["leadership", "communication", "problem-solving"],
    "experience_required_years": 3,
    "education_required": "Bachelor's in Computer Science or equivalent",
    "acronyms": {
        "AWS": "Amazon Web Services",
        "K8s": "Kubernetes",
        "CI/CD": "Continuous Integration / Continuous Deployment"
    },
    "job_title": "Senior Python Developer",
    "domain_keywords": ["payments", "fintech", "high-throughput"],
    "tools_and_frameworks": ["Docker", "Jenkins", "Terraform"],
    "total_keywords_count": 18
}

Rules:
- Include ALL technical terms, tools, frameworks, and methodologies mentioned
- Separate required vs preferred skills based on wording ("must have" vs "nice to have")
- Extract acronyms and their full forms
- Include domain-specific keywords (e.g., "payments", "e-commerce")
- If experience years not stated, set to null
- If education not stated, set to null"""


class JDExtractor:
    """Extracts structured skill/requirement data from job descriptions."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()

    def extract(self, job_text: str) -> dict[str, Any]:
        """
        Extract structured requirements from a job description.

        Args:
            job_text: Raw job description text

        Returns:
            Structured dict with skills, requirements, acronyms
        """
        prompt = f"""Parse this job description and extract all skills and requirements.

Job Description:
---
{LLMService.sanitize_content(job_text[:4000], "JOB_DESCRIPTION")}
---

Extract the data as JSON following your schema."""

        result = self._llm.generate_structured(
            prompt=prompt,
            system=JD_EXTRACTION_SYSTEM,
            temperature=0.1,
        )

        # In MCP mode, return the prompt
        if result.get("requires_host_ai"):
            return {
                "status": "mcp_mode",
                "prompt": result["mcp_prompt"],
                "instruction": "Extract skills and requirements from the job description as JSON.",
            }

        # Ensure all expected keys exist with defaults
        return self._normalise(result)

    def _normalise(self, data: dict) -> dict[str, Any]:
        """Ensure all expected fields exist with sensible defaults."""
        return {
            "required_hard_skills": data.get("required_hard_skills", []),
            "preferred_hard_skills": data.get("preferred_hard_skills", []),
            "soft_skills": data.get("soft_skills", []),
            "experience_required_years": data.get("experience_required_years"),
            "education_required": data.get("education_required"),
            "acronyms": data.get("acronyms", {}),
            "job_title": data.get("job_title", "Unknown"),
            "domain_keywords": data.get("domain_keywords", []),
            "tools_and_frameworks": data.get("tools_and_frameworks", []),
            "total_keywords_count": data.get("total_keywords_count", 0),
        }
