"""
ATS Integrity Check — Layer 3: "Is It Complete?"

Uses regex for contact/date validation and Python logic for
employment gap detection and experience calculation.

Score: out of 20 points.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


# Regex patterns
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9](?:[\w.+-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[\w.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}")
PHONE_REGEX_IN = re.compile(r"(?:\+91[\s-]?)?\d{10}|(?:\+91[\s-]?)?\d{5}[\s-]?\d{5}")
PHONE_REGEX_INTL = re.compile(r"\+?\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}")

# Date patterns
DATE_MM_YYYY = re.compile(r"\b(0?[1-9]|1[0-2])[/\-](19|20)\d{2}\b")
DATE_MONTH_YYYY = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(19|20)\d{2}\b",
    re.IGNORECASE,
)
DATE_FUZZY = re.compile(
    r"\b(Spring|Summer|Autumn|Fall|Winter|Q[1-4])\s+(19|20)\d{2}\b",
    re.IGNORECASE,
)
DATE_BARE_YEAR = re.compile(r"\b(19|20)\d{2}\b")

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


class IntegrityCheck:
    """ATS Layer 3 — Data integrity and completeness checks."""

    MAX_SCORE = 20
    DEFAULT_GAP_THRESHOLD_MONTHS = 6

    def check(
        self,
        resume_data: dict[str, Any],
        resume_extract: dict[str, Any],
        jd_extract: dict[str, Any] | None = None,
        gap_threshold_months: int = 6,
    ) -> dict[str, Any]:
        """
        Run all Layer 3 integrity checks.

        Args:
            resume_data: Output from ResumeParserAgent.parse()
            resume_extract: Output from ResumeExtractor.extract()
            jd_extract: Optional, from JDExtractor.extract() — for comparison
            gap_threshold_months: Flag gaps longer than this

        Returns:
            Layer 3 result dict with score, issues, details
        """
        issues: list[dict[str, Any]] = []
        score = self.MAX_SCORE

        # Check 1: Contact info (regex)
        contact_issues, contact_penalty = self._check_contact(resume_data)
        issues.extend(contact_issues)
        score -= contact_penalty

        # Check 2: Date formats (regex)
        date_issues, date_penalty = self._check_dates(resume_data.get("raw_text", ""))
        issues.extend(date_issues)
        score -= date_penalty

        # Check 3: Employment gaps (from LLM extract)
        gap_issues, gap_penalty = self._check_gaps(
            resume_extract.get("job_titles", []),
            gap_threshold_months,
        )
        issues.extend(gap_issues)
        score -= gap_penalty

        # Check 4: Experience vs JD requirement
        if jd_extract:
            exp_issues, exp_penalty = self._check_experience(
                resume_extract.get("total_experience_years", 0),
                jd_extract.get("experience_required_years"),
            )
            issues.extend(exp_issues)
            score -= exp_penalty

            # Check 5: Education level
            edu_issues, edu_penalty = self._check_education(
                resume_extract.get("education", []),
                jd_extract.get("education_required"),
            )
            issues.extend(edu_issues)
            score -= edu_penalty

        return {
            "layer": 3,
            "name": "Data Integrity",
            "score": max(score, 0),
            "max_score": self.MAX_SCORE,
            "issues": issues,
            "summary": {
                "errors": sum(1 for i in issues if i["severity"] == "error"),
                "warnings": sum(1 for i in issues if i["severity"] == "warning"),
                "infos": sum(1 for i in issues if i["severity"] == "info"),
                "passed": all(i["severity"] != "error" for i in issues),
            },
        }

    def _check_contact(self, resume_data: dict) -> tuple[list[dict], int]:
        """Verify contact information is present."""
        issues = []
        penalty = 0
        text = resume_data.get("raw_text", "")

        # Email check
        emails = EMAIL_REGEX.findall(text)
        if emails:
            issues.append({
                "check": "contact_email",
                "severity": "pass",
                "message": f"Email found: {emails[0]}",
            })
        else:
            issues.append({
                "check": "contact_email",
                "severity": "error",
                "message": "No email address found in resume",
                "suggestion": "Add your email address to the resume body",
            })
            penalty += 3

        # Phone check
        phones_in = PHONE_REGEX_IN.findall(text)
        phones_intl = PHONE_REGEX_INTL.findall(text)
        if phones_in or phones_intl:
            phone = phones_in[0] if phones_in else phones_intl[0]
            issues.append({
                "check": "contact_phone",
                "severity": "pass",
                "message": f"Phone number found: {phone}",
            })
        else:
            issues.append({
                "check": "contact_phone",
                "severity": "warning",
                "message": "No phone number found in resume",
                "suggestion": "Add your phone number in +91-XXXXX-XXXXX format",
            })
            penalty += 2

        return issues, penalty

    def _check_dates(self, text: str) -> tuple[list[dict], int]:
        """Validate date formats in the resume text."""
        issues = []
        penalty = 0

        # Check for fuzzy dates
        fuzzy_dates = DATE_FUZZY.findall(text)
        if fuzzy_dates:
            examples = [f"{season} {year}" for season, year in fuzzy_dates[:3]]
            issues.append({
                "check": "date_format",
                "severity": "warning",
                "message": f"Fuzzy dates found: {', '.join(examples)}",
                "suggestion": "Use MM/YYYY or 'Month YYYY' format instead",
            })
            penalty += 1

        # Check for standard dates
        mm_yyyy = DATE_MM_YYYY.findall(text)
        month_yyyy = DATE_MONTH_YYYY.findall(text)

        if mm_yyyy or month_yyyy:
            total_standard = len(mm_yyyy) + len(month_yyyy)
            issues.append({
                "check": "date_format",
                "severity": "pass",
                "message": f"{total_standard} dates in standard format found",
            })
        elif not fuzzy_dates:
            # Check for any dates at all
            bare_years = DATE_BARE_YEAR.findall(text)
            if bare_years:
                issues.append({
                    "check": "date_format",
                    "severity": "info",
                    "message": "Only bare years found (e.g., '2023') — consider using 'Month YYYY' format",
                })

        return issues, penalty

    def _check_gaps(
        self, job_titles: list[dict], threshold_months: int
    ) -> tuple[list[dict], int]:
        """Detect employment gaps from structured job data."""
        issues = []
        penalty = 0

        if len(job_titles) < 2:
            return issues, penalty

        # Sort jobs by start date (most recent first)
        dated_jobs = []
        for job in job_titles:
            start = self._parse_date_str(job.get("start_date", ""))
            end = self._parse_date_str(job.get("end_date", ""))

            if start:
                dated_jobs.append({
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company", "Unknown"),
                    "start": start,
                    "end": end or datetime.now(),
                })

        dated_jobs.sort(key=lambda x: x["start"], reverse=True)

        # Check gaps between consecutive jobs
        for i in range(len(dated_jobs) - 1):
            current_start = dated_jobs[i]["start"]
            previous_end = dated_jobs[i + 1]["end"]

            gap_months = (current_start.year - previous_end.year) * 12 + (
                current_start.month - previous_end.month
            )

            if gap_months > threshold_months:
                gap_start = previous_end.strftime("%b %Y")
                gap_end = current_start.strftime("%b %Y")
                issues.append({
                    "check": "employment_gap",
                    "severity": "warning",
                    "message": f"{gap_months}-month gap ({gap_start} – {gap_end})",
                    "suggestion": "Consider adding context (freelance, education, sabbatical)",
                })
                penalty += 2

        penalty = min(penalty, 4)
        return issues, penalty

    def _check_experience(
        self, total_years: float, required_years: int | float | None
    ) -> tuple[list[dict], int]:
        """Compare candidate's experience against JD requirement."""
        issues = []
        penalty = 0

        if required_years is None:
            return issues, penalty

        if total_years >= required_years:
            issues.append({
                "check": "experience_years",
                "severity": "pass",
                "message": f"{total_years} years experience (JD requires {required_years}+)",
            })
        else:
            gap = required_years - total_years
            if gap <= 1:
                issues.append({
                    "check": "experience_years",
                    "severity": "info",
                    "message": f"{total_years} years detected (JD requires {required_years}+) — close enough, worth applying",
                })
            else:
                issues.append({
                    "check": "experience_years",
                    "severity": "warning",
                    "message": f"{total_years} years detected but JD requires {required_years}+ years",
                    "suggestion": "Consider highlighting project experience or freelance work",
                })
                penalty += 2

        return issues, penalty

    def _check_education(
        self, education: list[dict], required: str | None
    ) -> tuple[list[dict], int]:
        """Check education level against JD requirement."""
        issues = []
        penalty = 0

        if not required:
            return issues, penalty

        # Extract degree levels from education
        degree_levels = {
            "phd": 4, "doctorate": 4, "ph.d": 4,
            "master": 3, "mtech": 3, "mba": 3, "m.tech": 3, "m.s": 3, "ms": 3,
            "bachelor": 2, "btech": 2, "b.tech": 2, "b.s": 2, "bs": 2, "b.e": 2, "be": 2,
            "diploma": 1,
        }

        highest_level = 0
        highest_degree = "None"

        for edu in education:
            degree = edu.get("degree", "").lower()
            for key, level in degree_levels.items():
                if key in degree and level > highest_level:
                    highest_level = level
                    highest_degree = edu.get("degree", key)

        # Check required level
        required_level = 0
        required_lower = required.lower()
        for key, level in degree_levels.items():
            if key in required_lower:
                required_level = level
                break

        if highest_level >= required_level:
            issues.append({
                "check": "education",
                "severity": "pass",
                "message": f"Education: {highest_degree} (meets requirement)",
            })
        elif highest_level > 0:
            issues.append({
                "check": "education",
                "severity": "info",
                "message": f"Education: {highest_degree} — JD prefers {required}",
                "suggestion": "Relevant experience may compensate; worth applying",
            })

        return issues, penalty

    def _parse_date_str(self, date_str: str) -> datetime | None:
        """Parse a date string like '01/2021' or 'January 2021' into datetime."""
        if not date_str or date_str.lower() in ("present", "current", "now"):
            return None

        # Try MM/YYYY
        match = re.match(r"(\d{1,2})[/\-](\d{4})", date_str)
        if match:
            month, year = int(match.group(1)), int(match.group(2))
            return datetime(year, month, 1)

        # Try Month YYYY
        for month_name, month_num in MONTH_MAP.items():
            if month_name in date_str.lower():
                year_match = re.search(r"(\d{4})", date_str)
                if year_match:
                    return datetime(int(year_match.group(1)), month_num, 1)

        # Try bare year
        year_match = re.match(r"(\d{4})", date_str)
        if year_match:
            return datetime(int(year_match.group(1)), 1, 1)

        return None
