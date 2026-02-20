"""
Job Application Autopilot — MCP Server Entry Point

FastMCP server that exposes all tools for use with Claude Code,
Google Antigravity, or any other MCP-compatible AI assistant.

Usage:
    # Direct run
    python server.py

    # Via package entry point
    job-autopilot-server
"""

from __future__ import annotations

from fastmcp import FastMCP

from src.tools.parse_resume import parse_resume
from src.tools.profile_resume import profile_resume
from src.tools.fetch_job import fetch_job
from src.tools.ats_check import ats_check
from src.tools.tailor_resume import tailor_resume
from src.tools.generate_cover_letter import generate_cover_letter
from src.tools.export_resume import export_resume
from src.tools.search_jobs import search_jobs
from src.tools.track_applications import track_applications
from src.tools.apply_job import apply_job


# Create the MCP server
mcp = FastMCP("Job Application Autopilot")


# ── Resume Tools ─────────────────────────────────────────────

@mcp.tool()
async def tool_parse_resume(file_path: str) -> dict:
    """Parse a resume file (PDF/DOCX) into structured JSON using IBM Docling."""
    return await parse_resume(file_path)


@mcp.tool()
async def tool_profile_resume(resume_data: dict) -> dict:
    """Extract a professional profile — skills, experience level, best-fit roles."""
    return await profile_resume(resume_data)


@mcp.tool()
async def tool_export_resume(
    resume_text: str,
    contact: dict | None = None,
    sections: dict | None = None,
    filename: str | None = None,
    job_title: str | None = None,
    company: str | None = None,
) -> dict:
    """Export a resume to a formatted DOCX file."""
    return await export_resume(resume_text, contact, sections, filename, job_title, company)


# ── Job Tools ────────────────────────────────────────────────

@mcp.tool()
async def tool_fetch_job(
    url: str | None = None,
    text: str | None = None,
    title: str | None = None,
) -> dict:
    """Fetch and parse a job description from a URL or pasted text."""
    return await fetch_job(url, text, title)


@mcp.tool()
async def tool_search_jobs(
    query: str,
    platforms: list[str] | None = None,
    location: str | None = None,
    experience_level: str | None = None,
    max_per_platform: int = 10,
) -> dict:
    """Search for jobs across LinkedIn, Naukri, Indeed, and more."""
    return await search_jobs(query, platforms, location, experience_level, max_per_platform)


# ── ATS Tools ────────────────────────────────────────────────

@mcp.tool()
async def tool_ats_check(
    resume_data: dict,
    job_text: str,
    job_title: str = "Unknown Role",
    company: str = "Unknown Company",
) -> dict:
    """Run a full 3-layer ATS compatibility check on a resume."""
    return await ats_check(resume_data, job_text, job_title, company)


# ── Tailoring & Cover Letter ────────────────────────────────

@mcp.tool()
async def tool_tailor_resume(
    resume_data: dict,
    job_data: dict,
    ats_report: dict | None = None,
) -> dict:
    """Generate a tailored resume for a specific job. ⚠️ REQUIRES USER CONFIRMATION."""
    return await tailor_resume(resume_data, job_data, ats_report)


@mcp.tool()
async def tool_generate_cover_letter(
    resume_data: dict,
    job_data: dict,
    profile: dict | None = None,
    tone: str = "professional",
) -> dict:
    """Generate a personalised cover letter for a job application."""
    return await generate_cover_letter(resume_data, job_data, profile, tone)


# ── Application Management ──────────────────────────────────

@mcp.tool()
async def tool_track_applications(
    action: str = "dashboard",
    app_id: int | None = None,
    new_status: str | None = None,
    notes: str | None = None,
) -> dict:
    """View and manage job application tracking (dashboard/update/history/list)."""
    return await track_applications(action, app_id, new_status, notes)


@mcp.tool()
async def tool_apply_job(
    resume_id: int,
    job_db_id: int,
    tailored_text: str | None = None,
    cover_letter: str | None = None,
    ats_score: int | None = None,
    ats_report: dict | None = None,
    confirm: bool = False,
    app_id: int | None = None,
) -> dict:
    """Prepare and submit a job application. ⚠️ REQUIRES USER CONFIRMATION."""
    return await apply_job(
        resume_id, job_db_id, tailored_text,
        cover_letter, ats_score, ats_report, confirm, app_id,
    )


# ── Session Management ──────────────────────────────────────

@mcp.tool()
async def tool_save_session(platform: str) -> dict:
    """Save the current browser session cookies for a platform after manual login.

    Call this after logging in via a browser window opened by search_jobs.
    Supported platforms: linkedin, naukri, indeed.
    """
    from src.services.session_manager import SessionManager
    session = SessionManager()
    try:
        path = await session.save_session(platform)
        return {"status": "saved", "platform": platform, "cookie_file": path}
    except RuntimeError as e:
        return {"error": str(e), "hint": "You need an active browser session first. Run a search_jobs call to trigger login."}


# ── Server Entry Point ──────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
