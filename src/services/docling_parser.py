"""
Docling Document Parser — wraps IBM Research's Docling library.

Converts PDF/DOCX files into structured JSON with:
- Section detection (headers, body, lists)
- Reading order preservation
- Header/footer detection (critical for ATS Layer 1)
- Multi-column layout detection
- Table structure extraction
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Maximum resume file size in megabytes (configurable via env)
MAX_RESUME_SIZE_MB = int(os.getenv("MAX_RESUME_SIZE_MB", "10"))

from docling.document_converter import DocumentConverter


class DoclingParser:
    """Wraps Docling DocumentConverter for resume/document parsing."""

    def __init__(self) -> None:
        self._converter = DocumentConverter()

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        """
        Parse a PDF or DOCX file into structured JSON.

        Returns a dict with keys:
            - file_path: original file path
            - file_type: "pdf" or "docx"
            - text: full extracted plain text
            - sections: list of {type, level, text} dicts
            - tables: list of extracted tables
            - metadata: page count, has_header, has_footer, etc.
            - raw_document: the full Docling document export
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix not in (".pdf", ".docx"):
            raise ValueError(f"Unsupported file type: {suffix}. Only .pdf and .docx are accepted.")

        # Guard rail: file size limit
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_RESUME_SIZE_MB:
            raise ValueError(
                f"File too large ({size_mb:.1f} MB). "
                f"Maximum allowed size is {MAX_RESUME_SIZE_MB} MB."
            )

        try:
            result = self._converter.convert(str(path))
        except Exception as e:
            raise RuntimeError(
                f"Docling conversion failed for {path.name}: {e}. "
                "Ensure the file is a valid, non-corrupted PDF or DOCX."
            ) from e
        doc = result.document

        # Export the full document as a dict
        doc_dict = doc.export_to_dict()

        # Extract structured sections
        sections = self._extract_sections(doc_dict)

        # Extract tables
        tables = self._extract_tables(doc_dict)

        # Build metadata
        metadata = self._build_metadata(doc_dict, suffix)

        return {
            "file_path": str(path.resolve()),
            "file_type": suffix.lstrip("."),
            "text": doc.export_to_markdown(),
            "sections": sections,
            "tables": tables,
            "metadata": metadata,
            "raw_document": doc_dict,
        }

    def parse_to_json(self, file_path: str | Path) -> str:
        """Parse and return result as a JSON string."""
        return json.dumps(self.parse(file_path), indent=2, default=str)

    def _extract_sections(self, doc_dict: dict) -> list[dict[str, Any]]:
        """Extract sections from the Docling document dict."""
        sections: list[dict[str, Any]] = []
        body = doc_dict.get("body", {})

        for item in self._walk_content(body):
            content_type = item.get("content_type", "")
            text = item.get("text", "").strip()

            if not text:
                continue

            # Map Docling content types to our section types
            section_type = "text"
            level = 0

            if "heading" in content_type.lower() or "title" in content_type.lower():
                section_type = "heading"
                level = item.get("level", 1)
            elif "list" in content_type.lower():
                section_type = "list_item"
            elif "table" in content_type.lower():
                section_type = "table"

            sections.append({
                "type": section_type,
                "level": level,
                "text": text,
                "prov": item.get("prov", []),
            })

        return sections

    def _extract_tables(self, doc_dict: dict) -> list[dict[str, Any]]:
        """Extract table data from the Docling document dict."""
        tables: list[dict[str, Any]] = []

        for table in doc_dict.get("tables", []):
            table_data = {
                "num_rows": table.get("num_rows", 0),
                "num_cols": table.get("num_cols", 0),
                "cells": [],
            }

            for cell in table.get("data", {}).get("table_cells", []):
                table_data["cells"].append({
                    "row": cell.get("row_span", {}).get("start", 0),
                    "col": cell.get("col_span", {}).get("start", 0),
                    "text": cell.get("text", ""),
                })

            tables.append(table_data)

        return tables

    def _build_metadata(self, doc_dict: dict, file_type: str) -> dict[str, Any]:
        """Build metadata from the Docling document dict."""
        pages = doc_dict.get("pages", {})

        # Detect headers and footers
        has_header = False
        has_footer = False
        header_text = ""
        footer_text = ""

        for item in self._walk_content(doc_dict.get("body", {})):
            prov = item.get("prov", [])
            for p in prov:
                # Docling marks header/footer provenance
                if p.get("label", "").lower() in ("page_header", "header"):
                    has_header = True
                    header_text = item.get("text", "")
                elif p.get("label", "").lower() in ("page_footer", "footer"):
                    has_footer = True
                    footer_text = item.get("text", "")

        return {
            "file_type": file_type.lstrip("."),
            "page_count": len(pages) if isinstance(pages, dict) else 0,
            "has_header": has_header,
            "has_footer": has_footer,
            "header_text": header_text,
            "footer_text": footer_text,
        }

    def _walk_content(self, body: dict) -> list[dict]:
        """Recursively walk Docling body content and yield items."""
        items: list[dict] = []

        if isinstance(body, dict):
            children = body.get("children", [])
            if not children and body.get("text"):
                items.append(body)
            for child in children:
                items.extend(self._walk_content(child))
        elif isinstance(body, list):
            for item in body:
                items.extend(self._walk_content(item))

        return items
