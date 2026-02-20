"""
ATS Checker Agent — orchestrates all 3 layers of ATS analysis.

Coordinates:
- Layer 1: Formatting (Docling JSON) via FormatterCheck
- Layer 2: Keywords (LLM extracts) via JDExtractor + ResumeExtractor + KeywordScorer
- Layer 3: Integrity (regex + Python) via IntegrityCheck

Returns a complete ATS report with score, issues, and recommendations.
"""

from __future__ import annotations

from typing import Any

from src.ats.formatter_check import FormatterCheck
from src.ats.integrity_check import IntegrityCheck
from src.ats.jd_extractor import JDExtractor
from src.ats.keyword_scorer import KeywordScorer
from src.ats.report import ATSReport
from src.ats.resume_extractor import ResumeExtractor
from src.services.llm import LLMService


class ATSCheckerAgent:
    """Orchestrates the full 3-layer ATS analysis."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self._llm = llm or LLMService()
        self._formatter = FormatterCheck()
        self._jd_extractor = JDExtractor(self._llm)
        self._resume_extractor = ResumeExtractor(self._llm)
        self._keyword_scorer = KeywordScorer()
        self._integrity = IntegrityCheck()
        self._report = ATSReport()

    def check(
        self,
        resume_data: dict[str, Any],
        job_text: str,
        job_title: str = "Unknown Role",
        company: str = "Unknown Company",
    ) -> dict[str, Any]:
        """
        Run full ATS analysis on a resume against a job description.

        Args:
            resume_data: Output from ResumeParserAgent.parse()
            job_text: Raw job description text
            job_title: Job title for the report header
            company: Company name for the report header

        Returns:
            Complete ATS report dict with scores, issues, and formatted text
        """
        # Layer 1 — Formatting
        layer1 = self._formatter.check(resume_data)

        # Layer 2 — Keywords (requires LLM for extraction)
        jd_extract = self._jd_extractor.extract(job_text)
        resume_extract = self._resume_extractor.extract(resume_data.get("raw_text", ""))

        # Check if in MCP mode (LLM extracts need host AI processing)
        if jd_extract.get("status") == "mcp_mode" or resume_extract.get("status") == "mcp_mode":
            return self._mcp_partial_report(
                layer1, jd_extract, resume_extract, job_title, company
            )

        layer2 = self._keyword_scorer.score(
            jd_extract=jd_extract,
            resume_extract=resume_extract,
            resume_text=resume_data.get("raw_text", ""),
            resume_sections=resume_data.get("sections"),
        )

        # Layer 3 — Integrity
        layer3 = self._integrity.check(
            resume_data=resume_data,
            resume_extract=resume_extract,
            jd_extract=jd_extract,
        )

        # Build final report
        return self._report.format(
            layer1=layer1,
            layer2=layer2,
            layer3=layer3,
            job_title=job_title,
            company=company,
        )

    def check_with_extracts(
        self,
        resume_data: dict[str, Any],
        jd_extract: dict[str, Any],
        resume_extract: dict[str, Any],
        job_title: str = "Unknown Role",
        company: str = "Unknown Company",
    ) -> dict[str, Any]:
        """
        Run ATS analysis with pre-extracted LLM data.

        Use this in MCP mode after the host AI has processed
        the extraction prompts and returned structured JSON.

        Args:
            resume_data: Output from ResumeParserAgent.parse()
            jd_extract: Structured JD data (from host AI)
            resume_extract: Structured resume data (from host AI)
            job_title: Job title for the report header
            company: Company name for the report header

        Returns:
            Complete ATS report dict
        """
        layer1 = self._formatter.check(resume_data)

        layer2 = self._keyword_scorer.score(
            jd_extract=jd_extract,
            resume_extract=resume_extract,
            resume_text=resume_data.get("raw_text", ""),
            resume_sections=resume_data.get("sections"),
        )

        layer3 = self._integrity.check(
            resume_data=resume_data,
            resume_extract=resume_extract,
            jd_extract=jd_extract,
        )

        return self._report.format(
            layer1=layer1,
            layer2=layer2,
            layer3=layer3,
            job_title=job_title,
            company=company,
        )

    def _mcp_partial_report(
        self,
        layer1: dict,
        jd_extract: dict,
        resume_extract: dict,
        job_title: str,
        company: str,
    ) -> dict[str, Any]:
        """
        Return a partial report when in MCP mode.

        Layer 1 is complete (no LLM needed), but Layers 2 and 3
        need the host AI to process extraction prompts first.
        """
        return {
            "status": "mcp_mode",
            "layer1_complete": layer1,
            "jd_extraction_prompt": jd_extract.get("prompt", ""),
            "resume_extraction_prompt": resume_extract.get("prompt", ""),
            "job_title": job_title,
            "company": company,
            "instruction": (
                "Layer 1 (Formatting) is complete. To finish the ATS check:\n"
                "1. Process the JD extraction prompt and return structured JSON\n"
                "2. Process the resume extraction prompt and return structured JSON\n"
                "3. Call check_with_extracts() with both results to get the full report"
            ),
        }
