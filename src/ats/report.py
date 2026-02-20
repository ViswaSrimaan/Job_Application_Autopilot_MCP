"""
ATS Report Formatter — renders the final ATS score report.

Takes results from all 3 layers and produces a clean, readable
report card (both as structured dict and formatted text).
"""

from __future__ import annotations

from typing import Any


class ATSReport:
    """Formats ATS analysis results into a readable report."""

    GRADE_THRESHOLDS = {
        90: ("🟢", "Excellent"),
        75: ("🟡", "Good"),
        60: ("🟠", "Needs Improvement"),
        0: ("🔴", "Significant Issues"),
    }

    def format(
        self,
        layer1: dict[str, Any],
        layer2: dict[str, Any],
        layer3: dict[str, Any],
        job_title: str = "Unknown Role",
        company: str = "Unknown Company",
    ) -> dict[str, Any]:
        """
        Combine all 3 layers into a final ATS report.

        Returns:
            dict with overall_score, grade, layer summaries, and formatted text
        """
        overall_score = layer1["score"] + layer2["score"] + layer3["score"]
        max_score = layer1["max_score"] + layer2["max_score"] + layer3["max_score"]

        grade_icon, grade_label = self._get_grade(overall_score)

        report = {
            "job_title": job_title,
            "company": company,
            "overall_score": overall_score,
            "max_score": max_score,
            "grade": grade_label,
            "grade_icon": grade_icon,
            "layers": {
                "formatting": layer1,
                "keywords": layer2,
                "integrity": layer3,
            },
            "match_percentage": layer2.get("match_percentage", 0),
            "matched_keywords": layer2.get("matched_keywords", []),
            "missing_keywords": layer2.get("missing_keywords", []),
            "formatted_text": self._render_text(
                layer1, layer2, layer3, overall_score, max_score,
                grade_icon, grade_label, job_title, company,
            ),
        }

        return report

    def _get_grade(self, score: int) -> tuple[str, str]:
        """Get grade icon and label for a given score."""
        for threshold, (icon, label) in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return icon, label
        return "🔴", "Significant Issues"

    def _render_text(
        self,
        layer1: dict, layer2: dict, layer3: dict,
        overall: int, max_score: int,
        icon: str, label: str,
        job_title: str, company: str,
    ) -> str:
        """Render the report as formatted text."""
        lines = [
            f"ATS Report — {company} {job_title}",
            "━" * 50,
            f"Overall Score:       {overall} / {max_score}   {icon}  {label}",
            "",
        ]

        # Layer 1
        lines.append(f"Layer 1 — Formatting:   {layer1['score']} / {layer1['max_score']}")
        for issue in layer1.get("issues", []):
            icon_map = {"pass": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
            severity = issue.get("severity", "info")
            icon_char = icon_map.get(severity, "ℹ️")
            lines.append(f"  {icon_char} {issue['message']}")
        lines.append("")

        # Layer 2
        lines.append(f"Layer 2 — Keywords:     {layer2['score']} / {layer2['max_score']}")
        match_pct = layer2.get("match_percentage", 0)
        total_matched = layer2.get("total_matched", 0)
        total_jd = layer2.get("total_jd_keywords", 0)
        lines.append(f"  Match: {match_pct}% ({total_matched}/{total_jd} JD keywords found)")

        for issue in layer2.get("issues", []):
            severity = issue.get("severity", "info")
            icon_map = {"pass": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
            icon_char = icon_map.get(severity, "ℹ️")
            lines.append(f"  {icon_char} {issue['message']}")
        lines.append("")

        # Layer 3
        lines.append(f"Layer 3 — Integrity:    {layer3['score']} / {layer3['max_score']}")
        for issue in layer3.get("issues", []):
            severity = issue.get("severity", "info")
            icon_map = {"pass": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
            icon_char = icon_map.get(severity, "ℹ️")
            lines.append(f"  {icon_char} {issue['message']}")
        lines.append("")

        # Recommendation
        if overall >= 90:
            lines.append("Recommendation: Resume is well-optimised. Ready to apply!")
        elif overall >= 75:
            lines.append("Recommendation: Minor improvements possible. Consider tailoring.")
        elif overall >= 60:
            lines.append("Recommendation: Tailor resume to fix the above before applying.")
        else:
            lines.append("Recommendation: Significant changes needed before applying.")

        lines.append("━" * 50)

        return "\n".join(lines)
