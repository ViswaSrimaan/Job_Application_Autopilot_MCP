"""
Reference Agent — matches a target role to reference resumes.

Looks up the local reference resume library, finds the best match
for the user's target role, and returns the reference resume data
for benchmarking.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReferenceAgent:
    """Matches roles to reference resumes and provides benchmarking data."""

    def __init__(self, reference_dir: str | Path | None = None) -> None:
        self._ref_dir = Path(reference_dir or "reference_resumes")
        self._index: dict[str, Any] | None = None

    def _load_index(self) -> dict[str, Any]:
        """Load the reference resume index."""
        if self._index is not None:
            return self._index

        index_path = self._ref_dir / "index.json"
        if not index_path.exists():
            self._index = {"roles": {}}
            return self._index

        with open(index_path, "r", encoding="utf-8") as f:
            self._index = json.load(f)
        return self._index

    def find_references(
        self,
        role_title: str,
        max_results: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Find reference resumes matching a role title.

        Args:
            role_title: Target role (e.g., "Senior Python Developer")
            max_results: Maximum number of references to return

        Returns:
            List of reference resume data dicts, sorted by relevance
        """
        index = self._load_index()
        role_lower = role_title.lower()
        matches = []

        for role_key, role_data in index.get("roles", {}).items():
            keywords = role_data.get("keywords", [])
            # Score based on keyword overlap
            score = 0
            for keyword in keywords:
                if keyword.lower() in role_lower or role_lower in keyword.lower():
                    score += 2
                elif any(word in role_lower for word in keyword.lower().split()):
                    score += 1

            if score > 0:
                for file_path in role_data.get("files", []):
                    full_path = self._ref_dir / file_path
                    if full_path.exists():
                        try:
                            with open(full_path, "r", encoding="utf-8") as f:
                                ref_data = json.load(f)
                            matches.append({
                                "role_category": role_key,
                                "file": str(file_path),
                                "score": score,
                                "data": ref_data,
                            })
                        except (json.JSONDecodeError, IOError):
                            continue

        # Sort by relevance score
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:max_results]

    def get_benchmark(
        self,
        role_title: str,
        user_resume_sections: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """
        Get a benchmark comparison against reference resumes.

        Returns a dict with reference data and comparison notes.
        """
        references = self.find_references(role_title)

        if not references:
            return {
                "found": False,
                "message": f"No reference resumes found for '{role_title}'",
                "suggestion": "Reference resumes will be added over time. You can contribute yours!",
            }

        best_ref = references[0]

        return {
            "found": True,
            "role_category": best_ref["role_category"],
            "reference_file": best_ref["file"],
            "reference_data": best_ref["data"],
            "total_references_found": len(references),
            "all_references": [
                {"file": r["file"], "category": r["role_category"]}
                for r in references
            ],
        }

    def list_available_roles(self) -> list[str]:
        """List all role categories with available reference resumes."""
        index = self._load_index()
        return list(index.get("roles", {}).keys())

    def add_reference(
        self,
        role_category: str,
        file_name: str,
        data: dict[str, Any],
    ) -> str:
        """
        Add a new reference resume to the library.

        Args:
            role_category: Category key (e.g., "software_engineer")
            file_name: File name (e.g., "senior_dev_ref3.json")
            data: Pre-parsed resume data

        Returns:
            Path to the saved file
        """
        # Ensure directory exists
        role_dir = self._ref_dir / role_category
        role_dir.mkdir(parents=True, exist_ok=True)

        # Save the reference
        file_path = role_dir / file_name
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        # Update index
        index = self._load_index()
        if role_category not in index.get("roles", {}):
            index["roles"][role_category] = {
                "keywords": [role_category.replace("_", " ")],
                "files": [],
            }

        relative_path = f"{role_category}/{file_name}"
        if relative_path not in index["roles"][role_category]["files"]:
            index["roles"][role_category]["files"].append(relative_path)

        # Save updated index
        with open(self._ref_dir / "index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

        self._index = None  # Reset cache
        return str(file_path)
