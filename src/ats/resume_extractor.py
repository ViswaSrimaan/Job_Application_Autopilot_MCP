"""
Resume Extractor — LLM structured output for resume skill analysis.

Extracts hard skills (explicit + inferred), soft skills, job titles,
dates, and experience details from resume text using LLM JSON mode.

Key feature: detects INFERRED skills — skills demonstrated in bullet
text but not explicitly listed (e.g., "led the React rewrite" → React).
"""

from __future__ import annotations

from typing import Any

from src.services.llm import LLMService


RESUME_EXTRACTION_SYSTEM = """You are an expert resume analyst.
Extract ALL skills, experience, and qualifications from this resume.
Pay special attention to INFERRED skills — skills demonstrated in
bullet text but not explicitly listed in a skills section.

Respond ONLY with valid JSON matching this exact schema:

{
    "hard_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
    "inferred_skills": [
        {
            "skill": "React",
            "evidence": "led the frontend rewrite in React",
            "confidence": "high"
        },
        {
            "skill": "Team Leadership",
            "evidence": "managed a team of 5 engineers",
            "confidence": "high"
        }
    ],
    "soft_skills": ["team leadership", "mentoring", "communication"],
    "job_titles": [
        {
            "title": "Senior Software Engineer",
            "company": "Acme Corp",
            "start_date": "01/2021",
            "end_date": "present",
            "duration_months": 36
        }
    ],
    "total_experience_years": 4.5,
    "education": [
        {
            "degree": "Bachelor of Technology",
            "field": "Computer Science",
            "institution": "IIT Delhi",
            "year": 2019
        }
    ],
    "certifications": ["AWS Solutions Architect"],
    "domains": ["FinTech", "E-commerce"],
    "acronyms_used": {"AWS": true, "Amazon Web Services": false}
}

Rules:
- List ALL hard skills explicitly mentioned anywhere in the resume
- For inferred_skills, identify skills demonstrated in bullet points
  but not listed in any skills section. Rate confidence: high/medium/low
- Extract ALL job titles with dates in MM/YYYY format where available
- Calculate total_experience_years from employment dates
- For acronyms_used, note which form appears in the resume (short/long/both)"""


class ResumeExtractor:
    """Extracts structured skill/experience data from resume text."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()

    def extract(self, resume_text: str) -> dict[str, Any]:
        """
        Extract structured skills and experience from resume text.

        Args:
            resume_text: Raw resume text (from Docling)

        Returns:
            Structured dict with skills, titles, dates, education
        """
        prompt = f"""Analyse this resume and extract all skills and experience data.

Resume Text:
---
{LLMService.sanitize_content(resume_text[:5000], "RESUME")}
---

Extract the data as JSON following your schema. Be thorough — don't miss inferred skills."""

        result = self._llm.generate_structured(
            prompt=prompt,
            system=RESUME_EXTRACTION_SYSTEM,
            temperature=0.1,
        )

        if result.get("requires_host_ai"):
            return {
                "status": "mcp_mode",
                "prompt": result["mcp_prompt"],
                "instruction": "Extract skills and experience from the resume as JSON.",
            }

        return self._normalise(result)

    def _normalise(self, data: dict) -> dict[str, Any]:
        """Ensure all expected fields exist with sensible defaults."""
        return {
            "hard_skills": data.get("hard_skills", []),
            "inferred_skills": data.get("inferred_skills", []),
            "soft_skills": data.get("soft_skills", []),
            "job_titles": data.get("job_titles", []),
            "total_experience_years": data.get("total_experience_years", 0),
            "education": data.get("education", []),
            "certifications": data.get("certifications", []),
            "domains": data.get("domains", []),
            "acronyms_used": data.get("acronyms_used", {}),
        }

    def get_all_skills(self, extracted: dict) -> list[str]:
        """Get a flat list of all skills (explicit + inferred)."""
        skills = list(extracted.get("hard_skills", []))

        for inferred in extracted.get("inferred_skills", []):
            skill = inferred.get("skill", "") if isinstance(inferred, dict) else str(inferred)
            if skill and skill not in skills:
                skills.append(skill)

        return skills
