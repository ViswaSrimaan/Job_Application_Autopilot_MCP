"""
Cover Letter Agent — generates personalised cover letters.

Uses the LLM (CLI mode) or returns structured prompts (MCP mode)
to create a professional cover letter based on the resume profile
and job description.
"""

from __future__ import annotations

from typing import Any

from src.services.llm import LLMService


COVER_LETTER_SYSTEM_PROMPT = """You are a professional cover letter writer.
Write a personalised, compelling cover letter for the candidate applying to this role.

Rules:
- Keep it under 400 words
- Open with a strong hook — not "I am writing to apply for..."
- Highlight 2-3 specific achievements that match the job requirements
- Show genuine interest in the company/role
- Use a professional but warm tone
- Close with a call to action
- Do NOT use generic filler phrases
- Tailor every sentence to the specific job and company

Respond with the cover letter text only — no JSON, no markdown headers."""


class CoverLetterAgent:
    """Generates personalised cover letters."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()

    def generate(
        self,
        resume_data: dict[str, Any],
        job_data: dict[str, Any],
        profile: dict[str, Any] | None = None,
        tone: str = "professional",
    ) -> dict[str, Any]:
        """
        Generate a cover letter for a specific job application.

        Args:
            resume_data: Parsed resume from ResumeParserAgent
            job_data: Structured job data from JobFetcherAgent
            profile: Optional resume profile from ResumeProfiler
            tone: Writing tone (professional, warm, bold)

        Returns:
            dict with cover_letter text and metadata
        """
        # Build the context
        resume_text = resume_data.get("raw_text", "")
        contact = resume_data.get("contact", {})

        job_title = job_data.get("title", "the role")
        company = job_data.get("company", "the company")
        job_desc = job_data.get("full_description") or job_data.get("description_summary", "")
        requirements = job_data.get("requirements", {})

        # Build the prompt
        prompt = f"""Write a cover letter for this application:

CANDIDATE:
Name: {contact.get('name', 'the candidate')}
Current Title: {profile.get('current_title', 'N/A') if profile else 'N/A'}
Key Skills: {', '.join(profile.get('hard_skills', [])[:8]) if profile else 'See resume'}

RESUME HIGHLIGHTS:
{LLMService.sanitize_content(resume_text[:2000], "RESUME")}

JOB DETAILS:
Title: {job_title}
Company: {company}
Location: {job_data.get('location', 'N/A')}

JOB DESCRIPTION:
{LLMService.sanitize_content(job_desc[:2000], "JOB_DESCRIPTION")}

REQUIREMENTS:
Must-have: {', '.join(requirements.get('must_have', [])) if isinstance(requirements, dict) else 'N/A'}
Nice-to-have: {', '.join(requirements.get('nice_to_have', [])) if isinstance(requirements, dict) else 'N/A'}

TONE: {tone}

Write the cover letter now. Address it to the hiring team at {company}."""

        response = self._llm.generate(
            prompt=prompt,
            system=COVER_LETTER_SYSTEM_PROMPT,
            temperature=0.5,
        )

        # In MCP mode, the response is the prompt for the host AI
        if self._llm.is_mcp_mode:
            return {
                "status": "mcp_mode",
                "prompt": response,
                "job_title": job_title,
                "company": company,
                "instruction": (
                    "The host AI should generate a personalised cover letter "
                    "based on the resume and job description provided above."
                ),
            }

        return {
            "cover_letter": response,
            "job_title": job_title,
            "company": company,
            "word_count": len(response.split()),
            "candidate_name": contact.get("name", "Unknown"),
        }
