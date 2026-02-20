"""
ATS Formatter Check — Layer 1: "Can I Read It?"

Analyses the Docling-parsed resume structure for formatting issues
that would cause problems with real ATS parsers (Workday, Taleo, Greenhouse).

Checks:
- File type validation (PDF/DOCX only)
- Multi-column layout detection
- Section header standardisation
- Contact info placement (body vs header/footer)
- Bullet style consistency
- Text structure quality

Score: out of 20 points.
"""

from __future__ import annotations

from typing import Any


# Standard ATS-friendly section headers
STANDARD_HEADERS = {
    "experience", "education", "skills", "summary", "projects",
    "certifications", "awards", "publications", "languages", "contact",
}

# Non-standard bullet characters that may cause ATS issues
PROBLEMATIC_BULLETS = {"→", "➤", "➜", "►", "★", "✦", "✓", "✔", "⬤", "◆", "◇", "▪", "▸"}


class FormatterCheck:
    """ATS Layer 1 — Formatting and structure analysis."""

    MAX_SCORE = 20

    def check(self, resume_data: dict[str, Any]) -> dict[str, Any]:
        """
        Run all Layer 1 formatting checks.

        Args:
            resume_data: Output from ResumeParserAgent.parse()

        Returns:
            dict with score, max_score, issues list, and details
        """
        issues: list[dict[str, Any]] = []
        score = self.MAX_SCORE

        # Check 1: File type
        file_check = self._check_file_type(resume_data)
        if file_check:
            issues.append(file_check)
            if file_check["severity"] == "error":
                score -= 20  # Hard block
                return self._build_result(max(score, 0), issues)

        # Check 2: Section headers
        header_issues, header_penalty = self._check_section_headers(resume_data)
        issues.extend(header_issues)
        score -= header_penalty

        # Check 3: Contact info placement
        contact_issues, contact_penalty = self._check_contact_placement(resume_data)
        issues.extend(contact_issues)
        score -= contact_penalty

        # Check 4: Multi-column layout
        layout_issues, layout_penalty = self._check_layout(resume_data)
        issues.extend(layout_issues)
        score -= layout_penalty

        # Check 5: Bullet style
        bullet_issues, bullet_penalty = self._check_bullets(resume_data)
        issues.extend(bullet_issues)
        score -= bullet_penalty

        return self._build_result(max(score, 0), issues)

    def _check_file_type(self, resume_data: dict) -> dict | None:
        """Check if file type is ATS-compatible."""
        file_type = resume_data.get("file_info", {}).get("type", "unknown")

        if file_type not in ("pdf", "docx"):
            return {
                "check": "file_type",
                "severity": "error",
                "message": f"File type .{file_type} not accepted — only .pdf and .docx are ATS-compatible",
                "suggestion": "Convert your resume to PDF or DOCX format",
            }

        return None

    def _check_section_headers(self, resume_data: dict) -> tuple[list[dict], int]:
        """Check section headers against ATS-standard names."""
        issues = []
        penalty = 0

        original_headers = resume_data.get("section_headers", [])

        for header in original_headers:
            if not header.get("is_standard"):
                canonical = header.get("canonical", "other")
                if canonical != "other":
                    issues.append({
                        "check": "section_header",
                        "severity": "warning",
                        "message": f'Section header "{header["original"]}" is non-standard',
                        "suggestion": f'Rename to "{canonical.title()}" for better ATS parsing',
                    })
                    penalty += 1
                else:
                    issues.append({
                        "check": "section_header",
                        "severity": "info",
                        "message": f'Unrecognised section header: "{header["original"]}"',
                        "suggestion": "Consider using a standard header name",
                    })

        # Cap header penalties
        penalty = min(penalty, 3)
        return issues, penalty

    def _check_contact_placement(self, resume_data: dict) -> tuple[list[dict], int]:
        """Check that contact info is in body text, not header/footer."""
        issues = []
        penalty = 0

        metadata = resume_data.get("metadata", {})
        warnings = metadata.get("warnings", [])

        for warning in warnings:
            if "header" in warning.lower() or "footer" in warning.lower():
                issues.append({
                    "check": "contact_placement",
                    "severity": "warning",
                    "message": warning,
                    "suggestion": "Move contact information to the main body of the resume",
                })
                penalty += 1

        penalty = min(penalty, 2)
        return issues, penalty

    def _check_layout(self, resume_data: dict) -> tuple[list[dict], int]:
        """Check for multi-column layout issues."""
        issues = []
        penalty = 0

        raw_doc = resume_data.get("raw_document", {}) if "raw_document" in resume_data else {}

        # Check Docling metadata for column detection
        # Docling's document structure can indicate multi-column layouts
        body = raw_doc.get("body", {})
        if self._detect_columns(body):
            issues.append({
                "check": "layout",
                "severity": "warning",
                "message": "Multi-column layout detected — may cause text jumbling in ATS parsers",
                "suggestion": "Use a single-column layout for best ATS compatibility",
            })
            penalty += 2

        return issues, penalty

    def _detect_columns(self, body: dict) -> bool:
        """Detect if the document uses a multi-column layout via Docling data."""
        # Check for content items with horizontal position variations
        # that suggest multiple columns
        if not body:
            return False

        items = self._collect_items_with_bbox(body)
        if len(items) < 4:
            return False

        # If items have significantly different x-positions, it's likely multi-column
        x_positions = sorted(set(item["x"] for item in items if item.get("x") is not None))
        if len(x_positions) >= 2:
            # Check if the gap between distinct x-positions is significant
            gaps = [x_positions[i + 1] - x_positions[i] for i in range(len(x_positions) - 1)]
            if any(gap > 200 for gap in gaps):  # Significant horizontal gap
                return True

        return False

    def _collect_items_with_bbox(self, node: dict | list) -> list[dict]:
        """Collect all content items with bounding box positions."""
        items = []

        if isinstance(node, dict):
            prov = node.get("prov", [])
            for p in prov:
                bbox = p.get("bbox", {})
                if bbox:
                    items.append({
                        "x": bbox.get("l", bbox.get("x", None)),
                        "text": node.get("text", ""),
                    })

            for child in node.get("children", []):
                items.extend(self._collect_items_with_bbox(child))
        elif isinstance(node, list):
            for item in node:
                items.extend(self._collect_items_with_bbox(item))

        return items

    def _check_bullets(self, resume_data: dict) -> tuple[list[dict], int]:
        """Check for non-standard bullet characters."""
        issues = []
        penalty = 0

        raw_text = resume_data.get("raw_text", "")

        found_problematic = set()
        for char in PROBLEMATIC_BULLETS:
            if char in raw_text:
                found_problematic.add(char)

        if found_problematic:
            chars = ", ".join(f'"{c}"' for c in found_problematic)
            issues.append({
                "check": "bullet_style",
                "severity": "info",
                "message": f"Non-standard bullet characters found: {chars}",
                "suggestion": 'Replace with standard bullets: "•" or "-"',
            })
            penalty += 1

        return issues, penalty

    def _build_result(self, score: int, issues: list[dict]) -> dict[str, Any]:
        """Build the Layer 1 result dict."""
        # Count by severity
        errors = sum(1 for i in issues if i["severity"] == "error")
        warnings = sum(1 for i in issues if i["severity"] == "warning")
        infos = sum(1 for i in issues if i["severity"] == "info")

        return {
            "layer": 1,
            "name": "Formatting & Structure",
            "score": score,
            "max_score": self.MAX_SCORE,
            "issues": issues,
            "summary": {
                "errors": errors,
                "warnings": warnings,
                "infos": infos,
                "passed": len(issues) == 0,
            },
        }
