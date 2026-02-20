"""
Diff Viewer — shows changes between original and tailored resumes.

Generates a diff-style view highlighting changes, additions, and
removals. Used by the Tailor Agent to show the user what changed
before they confirm.
"""

from __future__ import annotations

import difflib
from typing import Any


class DiffViewer:
    """Shows structured diffs between resume versions."""

    def diff(
        self,
        original_text: str,
        modified_text: str,
        context_lines: int = 3,
    ) -> dict[str, Any]:
        """
        Generate a diff between original and modified resume text.

        Args:
            original_text: Original resume text
            modified_text: Modified resume text
            context_lines: Number of context lines around changes

        Returns:
            dict with diff lines, statistics, and formatted output
        """
        original_lines = original_text.splitlines(keepends=True)
        modified_lines = modified_text.splitlines(keepends=True)

        # Fast path: no diff needed if texts are identical
        if original_text == modified_text:
            return {
                "diff_text": "",
                "statistics": {
                    "additions": 0,
                    "deletions": 0,
                    "total_changes": 0,
                    "original_lines": len(original_lines),
                    "modified_lines": len(modified_lines),
                },
                "changes": [],
                "formatted": "No changes detected.",
                "has_changes": False,
            }

        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="Original Resume",
            tofile="Tailored Resume",
            n=context_lines,
        ))

        # Calculate statistics
        additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        # Generate structured changes
        changes = self._extract_changes(original_lines, modified_lines)

        return {
            "diff_text": "".join(diff_lines),
            "statistics": {
                "additions": additions,
                "deletions": deletions,
                "total_changes": additions + deletions,
                "original_lines": len(original_lines),
                "modified_lines": len(modified_lines),
            },
            "changes": changes,
            "formatted": self._format_changes(changes),
            "has_changes": additions + deletions > 0,
        }

    def diff_sections(
        self,
        original_sections: dict[str, list[str]],
        modified_sections: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Compare sections between original and modified resumes.

        Returns per-section diff analysis.
        """
        all_section_keys = set(list(original_sections.keys()) + list(modified_sections.keys()))
        section_diffs = {}

        for section in all_section_keys:
            orig_content = "\n".join(original_sections.get(section, []))
            mod_content = "\n".join(modified_sections.get(section, []))

            if orig_content != mod_content:
                section_diffs[section] = self.diff(orig_content, mod_content)
            else:
                section_diffs[section] = {
                    "has_changes": False,
                    "statistics": {"additions": 0, "deletions": 0, "total_changes": 0},
                }

        return {
            "section_diffs": section_diffs,
            "changed_sections": [
                s for s, d in section_diffs.items() if d.get("has_changes")
            ],
            "unchanged_sections": [
                s for s, d in section_diffs.items() if not d.get("has_changes")
            ],
        }

    def _extract_changes(
        self,
        original_lines: list[str],
        modified_lines: list[str],
    ) -> list[dict[str, Any]]:
        """Extract structured change descriptions."""
        changes = []

        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            change = {
                "type": tag,
                "original_range": (i1 + 1, i2),
                "modified_range": (j1 + 1, j2),
            }

            if tag == "replace":
                change["original_text"] = "".join(original_lines[i1:i2]).strip()
                change["modified_text"] = "".join(modified_lines[j1:j2]).strip()
                change["description"] = f"Lines {i1 + 1}–{i2} modified"
            elif tag == "insert":
                change["modified_text"] = "".join(modified_lines[j1:j2]).strip()
                change["description"] = f"New content added after line {i1}"
            elif tag == "delete":
                change["original_text"] = "".join(original_lines[i1:i2]).strip()
                change["description"] = f"Lines {i1 + 1}–{i2} removed"

            changes.append(change)

        return changes

    def _format_changes(self, changes: list[dict]) -> str:
        """Format changes as readable text."""
        if not changes:
            return "No changes detected."

        lines = [f"Found {len(changes)} change(s):\n"]

        for i, change in enumerate(changes, 1):
            change_type = change["type"]
            icon = {"replace": "✏️", "insert": "➕", "delete": "➖"}.get(change_type, "•")
            lines.append(f"{icon} Change {i}: {change['description']}")

            if "original_text" in change:
                preview = change["original_text"][:100]
                lines.append(f'  Original: "{preview}"')
            if "modified_text" in change:
                preview = change["modified_text"][:100]
                lines.append(f'  Modified: "{preview}"')

            lines.append("")

        return "\n".join(lines)
