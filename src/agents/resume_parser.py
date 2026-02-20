"""
Resume Parser Agent — converts resume files into structured JSON.

Uses Docling for document parsing, then organises the raw output
into a clean resume data structure with sections, contact info,
experience entries, skills, and education.
"""

from __future__ import annotations

import re
from typing import Any

from src.services.docling_parser import DoclingParser


class ResumeParserAgent:
    """Parses resume files (PDF/DOCX) into structured data."""

    # Standard section header names (variations mapped to canonical names)
    SECTION_MAP = {
        "experience": "experience",
        "work experience": "experience",
        "professional experience": "experience",
        "employment history": "experience",
        "career history": "experience",
        "work history": "experience",
        "education": "education",
        "academic background": "education",
        "qualifications": "education",
        "skills": "skills",
        "technical skills": "skills",
        "core competencies": "skills",
        "key skills": "skills",
        "expertise": "skills",
        "summary": "summary",
        "professional summary": "summary",
        "objective": "summary",
        "career objective": "summary",
        "profile": "summary",
        "about": "summary",
        "about me": "summary",
        "projects": "projects",
        "key projects": "projects",
        "certifications": "certifications",
        "certificates": "certifications",
        "awards": "awards",
        "achievements": "awards",
        "honours": "awards",
        "honors": "awards",
        "publications": "publications",
        "languages": "languages",
        "references": "references",
        "contact": "contact",
        "contact information": "contact",
        "personal details": "contact",
    }

    # Regex patterns for contact info extraction
    EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
    PHONE_PATTERN = re.compile(
        r"(?:\+91[\s-]?)?(?:\d{5}[\s-]?\d{5}|\d{10}|\d{3}[\s-]\d{3}[\s-]\d{4})"
    )
    LINKEDIN_PATTERN = re.compile(r"linkedin\.com/in/[\w-]+", re.IGNORECASE)
    GITHUB_PATTERN = re.compile(r"github\.com/[\w-]+", re.IGNORECASE)

    def __init__(self) -> None:
        self._parser = DoclingParser()

    def parse(self, file_path: str) -> dict[str, Any]:
        """
        Parse a resume file and return structured data.

        Returns:
            dict with keys:
                - file_info: path, type
                - contact: email, phone, linkedin, github, name
                - sections: dict mapping canonical section names to content
                - raw_text: full extracted text
                - metadata: page count, warnings, formatting info
                - section_headers: original headers found (for ATS)
        """
        # Parse via Docling
        doc = self._parser.parse(file_path)

        # Extract contact info from text
        contact = self._extract_contact(doc["text"])

        # Organise into sections
        sections, original_headers = self._organise_sections(doc["sections"], doc["text"])

        # Build the result
        return {
            "file_info": {
                "path": doc["file_path"],
                "type": doc["file_type"],
            },
            "contact": contact,
            "sections": sections,
            "section_headers": original_headers,
            "tables": doc["tables"],
            "raw_text": doc["text"],
            "raw_document": doc.get("raw_document", {}),
            "metadata": {
                **doc["metadata"],
                "warnings": self._check_warnings(doc, contact),
            },
        }

    def _extract_contact(self, text: str) -> dict[str, str | None]:
        """Extract contact information from resume text."""
        emails = self.EMAIL_PATTERN.findall(text)
        phones = self.PHONE_PATTERN.findall(text)
        linkedin = self.LINKEDIN_PATTERN.findall(text)
        github = self.GITHUB_PATTERN.findall(text)

        # Try to extract name — usually the first line of text
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        name = None
        if lines:
            first_line = lines[0]
            # Name is likely the first line if it's short and doesn't contain @, http, etc.
            if len(first_line) < 60 and not any(c in first_line for c in ["@", "http", "://", "."]):
                name = first_line

        return {
            "name": name,
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
            "linkedin": linkedin[0] if linkedin else None,
            "github": github[0] if github else None,
            "all_emails": emails,
            "all_phones": phones,
        }

    def _organise_sections(
        self, sections: list[dict], full_text: str
    ) -> tuple[dict[str, Any], list[dict[str, str]]]:
        """
        Organise raw sections into canonical resume sections.

        Returns:
            - sections dict: canonical_name -> content list
            - original_headers: list of {original, canonical} mappings
        """
        organised: dict[str, list[str]] = {}
        original_headers: list[dict[str, str]] = []
        current_section = "header"

        for section in sections:
            if section["type"] == "heading":
                header_text = section["text"].strip()
                canonical = self._map_section(header_text)
                current_section = canonical or "other"

                original_headers.append({
                    "original": header_text,
                    "canonical": current_section,
                    "is_standard": canonical is not None,
                })
            else:
                if current_section not in organised:
                    organised[current_section] = []
                organised[current_section].append(section["text"])

        return organised, original_headers

    def _map_section(self, header: str) -> str | None:
        """Map a section header to its canonical name."""
        normalised = header.lower().strip().rstrip(":")
        return self.SECTION_MAP.get(normalised)

    def _check_warnings(self, doc: dict, contact: dict) -> list[str]:
        """Generate warnings about the resume structure."""
        warnings = []

        # Check for contact info in header/footer
        metadata = doc["metadata"]
        if metadata.get("has_header"):
            header_text = metadata.get("header_text", "")
            if contact["email"] and contact["email"] in header_text:
                warnings.append("Email found in page header — may be missed by ATS parsers")
            if contact["phone"] and contact["phone"] in header_text:
                warnings.append("Phone found in page header — may be missed by ATS parsers")

        if metadata.get("has_footer"):
            footer_text = metadata.get("footer_text", "")
            if contact["email"] and contact["email"] in footer_text:
                warnings.append("Email found in page footer — may be missed by ATS parsers")
            if contact["phone"] and contact["phone"] in footer_text:
                warnings.append("Phone found in page footer — may be missed by ATS parsers")

        # Check for missing contact info
        if not contact["email"]:
            warnings.append("No email address found in resume")
        if not contact["phone"]:
            warnings.append("No phone number found in resume")

        return warnings
