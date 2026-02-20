"""
Tailor Agent — generates a tailored resume for a specific job.

Uses the LLM to rewrite resume sections to better match job
requirements, then generates a diff for user confirmation.
"""

from __future__ import annotations

from typing import Any

from src.agents.diff_viewer import DiffViewer
from src.services.llm import LLMService


TAILOR_SYSTEM = """You are an expert resume writer and ATS optimisation specialist.
Modify the given resume sections to better match the job requirements.

Rules:
- Keep all factual information accurate — never fabricate experience
- Add relevant keywords naturally into existing bullet points
- Reorder bullets to prioritise the most relevant experience first
- Adjust the summary/objective to target the specific role
- Include both acronym and full-form versions of key terms
- Keep the same formatting and structure
- DO NOT remove any real experience or skills

Respond ONLY with the modified resume text — no JSON, no explanations."""


class TailorAgent:
    """Generates tailored resume content for specific job applications."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()
        self._diff_viewer = DiffViewer()

    def tailor(
        self,
        resume_data: dict[str, Any],
        job_data: dict[str, Any],
        jd_extract: dict[str, Any] | None = None,
        ats_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a tailored resume for a specific job.

        Args:
            resume_data: Parsed resume from ResumeParserAgent
            job_data: Structured job data from JobFetcherAgent
            jd_extract: JD extract from JDExtractor (optional, for keyword focus)
            ats_report: ATS report (optional, to address specific issues)

        Returns:
            dict with original text, tailored text, diff, and confirmation request
        """
        original_text = resume_data.get("raw_text", "")
        job_title = job_data.get("title", "the role")
        company = job_data.get("company", "the company")

        # Build the tailoring prompt
        missing_keywords = []
        if ats_report:
            missing_keywords = ats_report.get("missing_keywords", [])
        elif jd_extract:
            missing_keywords = jd_extract.get("required_hard_skills", [])

        requirements = job_data.get("requirements", {})

        prompt = f"""Tailor this resume for the following job application.

ORIGINAL RESUME:
---
{LLMService.sanitize_content(original_text[:3500], "RESUME")}
---

JOB DETAILS:
Title: {job_title}
Company: {company}
Description: {LLMService.sanitize_content((job_data.get('description_summary', job_data.get('full_description', 'N/A'))[:1000]), "JOB_DESCRIPTION")}

MUST-HAVE REQUIREMENTS: {', '.join(requirements.get('must_have', [])) if isinstance(requirements, dict) else 'N/A'}
NICE-TO-HAVE: {', '.join(requirements.get('nice_to_have', [])) if isinstance(requirements, dict) else 'N/A'}

MISSING KEYWORDS TO ADD NATURALLY: {', '.join(missing_keywords[:15]) if missing_keywords else 'None identified'}

ATS ISSUES TO FIX: {self._format_ats_issues(ats_report) if ats_report else 'No ATS report available'}

Rewrite the resume to better match this job. Follow the rules in your instructions."""

        response = self._llm.generate(
            prompt=prompt,
            system=TAILOR_SYSTEM,
            temperature=0.3,
        )

        # In MCP mode, return the prompt for the host AI
        if self._llm.is_mcp_mode:
            return {
                "status": "mcp_mode",
                "prompt": response,
                "original_text": original_text,
                "job_title": job_title,
                "company": company,
                "instruction": (
                    "The host AI should tailor the resume for this job. "
                    "After generating the tailored text, show the diff to the user for confirmation."
                ),
            }

        # Generate diff
        diff = self._diff_viewer.diff(original_text, response)

        return {
            "original_text": original_text,
            "tailored_text": response,
            "diff": diff,
            "job_title": job_title,
            "company": company,
            "requires_confirmation": True,
            "confirmation_message": (
                f"Review the changes above ({diff['statistics']['total_changes']} modifications). "
                "Do you want to apply these changes to your resume?"
            ),
        }

    def _format_ats_issues(self, ats_report: dict) -> str:
        """Extract actionable issues from ATS report."""
        if not ats_report:
            return "N/A"

        issues_text = []
        for layer_key in ["formatting", "keywords", "integrity"]:
            layer = ats_report.get("layers", {}).get(layer_key, {})
            for issue in layer.get("issues", []):
                if issue.get("severity") in ("warning", "error"):
                    suggestion = issue.get("suggestion", "")
                    msg = issue.get("message", "")
                    issues_text.append(f"- {msg}" + (f" → {suggestion}" if suggestion else ""))

        return "\n".join(issues_text[:10]) if issues_text else "No major issues"
