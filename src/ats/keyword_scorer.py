"""
ATS Keyword Scorer — Layer 2: "Is It Relevant?"

Pure Python scoring logic that compares LLM-extracted data from
the job description (JDExtractor) and resume (ResumeExtractor).

No NLP library needed — all intelligence comes from the LLM extracts.

Score: out of 60 points.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


class KeywordScorer:
    """ATS Layer 2 — Keyword matching and relevance scoring."""

    MAX_SCORE = 60

    # Scoring weights
    EXACT_MATCH_POINTS = 3
    INFERRED_MATCH_POINTS = 2
    DOMAIN_MATCH_POINTS = 2
    ACRONYM_BONUS = 1
    PLACEMENT_TITLE = 5
    PLACEMENT_EXPERIENCE = 3
    PLACEMENT_SKILLS = 1

    # Density thresholds
    KEYWORD_DENSITY_OPTIMAL_MIN = 0.01  # 1%
    KEYWORD_DENSITY_OPTIMAL_MAX = 0.03  # 3%
    KEYWORD_DENSITY_STUFFING = 0.05     # 5%

    def score(
        self,
        jd_extract: dict[str, Any],
        resume_extract: dict[str, Any],
        resume_text: str,
        resume_sections: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """
        Score resume keywords against job description requirements.

        Args:
            jd_extract: Output from JDExtractor.extract()
            resume_extract: Output from ResumeExtractor.extract()
            resume_text: Full resume text (for density analysis)
            resume_sections: Organised resume sections (for placement scoring)

        Returns:
            Layer 2 result dict with score, matches, missing keywords
        """
        issues: list[dict[str, Any]] = []
        score = 0

        # Collect all JD keywords
        jd_required = [s.lower() for s in jd_extract.get("required_hard_skills", [])]
        jd_preferred = [s.lower() for s in jd_extract.get("preferred_hard_skills", [])]
        jd_domains = [s.lower() for s in jd_extract.get("domain_keywords", [])]
        jd_tools = [s.lower() for s in jd_extract.get("tools_and_frameworks", [])]
        jd_all = list(set(jd_required + jd_preferred + jd_domains + jd_tools))

        # Collect all resume skills
        resume_hard = [s.lower() for s in resume_extract.get("hard_skills", [])]
        resume_inferred = []
        for item in resume_extract.get("inferred_skills", []):
            if isinstance(item, dict):
                resume_inferred.append(item.get("skill", "").lower())
            else:
                resume_inferred.append(str(item).lower())
        resume_all = list(set(resume_hard + resume_inferred))

        # 1. Exact keyword matching
        matched = []
        missing = []
        inferred_matches = []

        for keyword in jd_all:
            if keyword in resume_hard:
                matched.append(keyword)
            elif keyword in resume_inferred:
                inferred_matches.append(keyword)
            else:
                missing.append(keyword)

        # Calculate match scores
        exact_score = min(len(matched) * self.EXACT_MATCH_POINTS, 30)
        inferred_score = min(len(inferred_matches) * self.INFERRED_MATCH_POINTS, 10)
        score += exact_score + inferred_score

        # Record found keywords
        if matched:
            issues.append({
                "check": "keyword_match",
                "severity": "pass",
                "message": f"Found: {', '.join(matched[:15])}",
                "count": len(matched),
            })

        if inferred_matches:
            issues.append({
                "check": "inferred_match",
                "severity": "pass",
                "message": f"Inferred skills matched: {', '.join(inferred_matches[:10])}",
                "count": len(inferred_matches),
            })

        if missing:
            issues.append({
                "check": "missing_keywords",
                "severity": "warning",
                "message": f"Missing: {', '.join(missing[:15])}",
                "suggestion": "Add these keywords to your resume if you have the experience",
                "keywords": missing,
            })

        # 2. Match percentage
        total_jd = len(jd_all)
        total_matched = len(matched) + len(inferred_matches)
        match_pct = round((total_matched / total_jd * 100) if total_jd > 0 else 0, 1)

        # 3. Acronym check
        acronym_issues = self._check_acronyms(
            jd_extract.get("acronyms", {}),
            resume_extract.get("acronyms_used", {}),
            resume_text,
        )
        issues.extend(acronym_issues)
        score += min(sum(1 for i in acronym_issues if i["severity"] == "pass") * self.ACRONYM_BONUS, 5)

        # 4. Keyword density
        density_issues, density_bonus = self._check_density(jd_all, resume_text)
        issues.extend(density_issues)
        score += density_bonus

        # 5. Contextual placement scoring
        if resume_sections:
            placement_score = self._score_placement(jd_required, resume_sections)
            score += min(placement_score, 10)

        # Cap score
        score = min(score, self.MAX_SCORE)

        return {
            "layer": 2,
            "name": "Keywords & Relevance",
            "score": score,
            "max_score": self.MAX_SCORE,
            "match_percentage": match_pct,
            "matched_keywords": matched,
            "inferred_matches": inferred_matches,
            "missing_keywords": missing,
            "total_jd_keywords": total_jd,
            "total_matched": total_matched,
            "issues": issues,
            "summary": {
                "match_pct": match_pct,
                "matched": len(matched),
                "inferred": len(inferred_matches),
                "missing": len(missing),
            },
        }

    def _check_acronyms(
        self,
        jd_acronyms: dict[str, str],
        resume_acronyms: dict[str, bool],
        resume_text: str,
    ) -> list[dict[str, Any]]:
        """Check if resume includes both short and long forms of acronyms."""
        issues = []

        for short_form, long_form in jd_acronyms.items():
            has_short = short_form.lower() in resume_text.lower()
            has_long = long_form.lower() in resume_text.lower()

            if has_short and has_long:
                issues.append({
                    "check": "acronym",
                    "severity": "pass",
                    "message": f'Both "{short_form}" and "{long_form}" found',
                })
            elif has_short and not has_long:
                issues.append({
                    "check": "acronym",
                    "severity": "warning",
                    "message": f'"{short_form}" found but not "{long_form}" — include both',
                    "suggestion": f'Add "{long_form} ({short_form})" to your resume',
                })
            elif has_long and not has_short:
                issues.append({
                    "check": "acronym",
                    "severity": "warning",
                    "message": f'"{long_form}" found but not "{short_form}" — include both',
                    "suggestion": f'Add "{short_form}" alongside the full form',
                })

        return issues

    def _check_density(
        self,
        jd_keywords: list[str],
        resume_text: str,
    ) -> tuple[list[dict[str, Any]], int]:
        """Check keyword density in resume text."""
        issues = []
        bonus = 0

        words = resume_text.lower().split()
        total_words = len(words)

        if total_words == 0:
            return issues, bonus

        word_counts = Counter(words)

        for keyword in jd_keywords:
            keyword_lower = keyword.lower()
            # Count occurrences (handle multi-word keywords)
            if " " in keyword_lower:
                count = resume_text.lower().count(keyword_lower)
            else:
                count = word_counts.get(keyword_lower, 0)

            if count > 0:
                density = count / total_words
                if density > self.KEYWORD_DENSITY_STUFFING:
                    issues.append({
                        "check": "keyword_density",
                        "severity": "warning",
                        "message": f'"{keyword}" mentioned {count}× — density too high ({density:.1%})',
                        "suggestion": f"Aim for 2–3 mentions, currently at {count}",
                    })
                elif count >= 2 and density <= self.KEYWORD_DENSITY_OPTIMAL_MAX:
                    bonus += 1

        bonus = min(bonus, 5)
        return issues, bonus

    def _score_placement(
        self,
        required_keywords: list[str],
        sections: dict[str, list[str]],
    ) -> int:
        """Score keywords based on where they appear in the resume."""
        score = 0

        # Check skills section
        skills_text = " ".join(sections.get("skills", [])).lower()
        experience_text = " ".join(sections.get("experience", [])).lower()
        summary_text = " ".join(sections.get("summary", [])).lower()

        for keyword in required_keywords[:10]:
            kw_lower = keyword.lower()
            if kw_lower in summary_text:
                score += self.PLACEMENT_TITLE
            elif kw_lower in experience_text:
                score += self.PLACEMENT_EXPERIENCE
            elif kw_lower in skills_text:
                score += self.PLACEMENT_SKILLS

        return score
