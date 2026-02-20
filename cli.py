"""
Job Application Autopilot — CLI Entry Point

Typer-based CLI for standalone usage without an MCP host.
Provides all the same functionality as the MCP server.

Usage:
    job-autopilot --help
    job-autopilot parse resume.pdf
    job-autopilot profile resume.pdf
    job-autopilot ats resume.pdf --job-url https://...
    job-autopilot tailor resume.pdf --job-url https://...
    job-autopilot cover-letter resume.pdf --job-url https://...
    job-autopilot search "Python Developer" --location "Bangalore"
    job-autopilot dashboard
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.agents.ats_checker import ATSCheckerAgent
from src.agents.cover_letter_agent import CoverLetterAgent
from src.agents.job_fetcher import JobFetcherAgent
from src.agents.platform_agent import PlatformAgent
from src.agents.resume_parser import ResumeParserAgent
from src.agents.resume_profiler import ResumeProfiler
from src.agents.tailor_agent import TailorAgent
from src.agents.tracker_agent import TrackerAgent
from src.services.doc_exporter import DocExporter
from src.services.llm import LLMService
from src.storage.database import Database

app = typer.Typer(
    name="job-autopilot",
    help="AI-powered job application autopilot. Parse resumes, check ATS scores, tailor content, and apply.",
    add_completion=False,
)
console = Console()


def _get_llm() -> LLMService:
    """Get the configured LLM service."""
    return LLMService()


def _resolve_resume_path(file_path: str | None) -> str:
    """Resolve resume path from argument or RESUME_PATH env var."""
    path = file_path or os.getenv("RESUME_PATH")
    if not path:
        raise typer.BadParameter(
            "Provide a resume file path or set RESUME_PATH in .env"
        )
    return path


# ── Resume Commands ──────────────────────────────────────────

@app.command()
def parse(
    file_path: str = typer.Argument(None, help="Path to resume file (PDF or DOCX). Falls back to RESUME_PATH env var."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save JSON output to file"),
):
    """Parse a resume file into structured JSON."""
    file_path = _resolve_resume_path(file_path)
    parser = ResumeParserAgent()

    with console.status("Parsing resume..."):
        result = parser.parse(file_path)

    console.print(Panel(f"[bold green]Resume parsed successfully[/]", title="✅ Parse Complete"))
    console.print(f"  Name:    {result['contact'].get('name', 'N/A')}")
    console.print(f"  Email:   {result['contact'].get('email', 'N/A')}")
    console.print(f"  Phone:   {result['contact'].get('phone', 'N/A')}")
    console.print(f"  Type:    {result['file_info']['type']}")
    console.print(f"  Sections: {len(result.get('section_headers', []))}")

    warnings = result.get("metadata", {}).get("warnings", [])
    if warnings:
        console.print("\n[yellow]Warnings:[/]")
        for w in warnings:
            console.print(f"  ⚠️  {w}")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        console.print(f"\n📄 JSON saved to {output}")


@app.command()
def profile(
    file_path: str = typer.Argument(None, help="Path to resume file. Falls back to RESUME_PATH env var."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save profile JSON"),
):
    """Extract a professional profile from a resume."""
    file_path = _resolve_resume_path(file_path)
    parser = ResumeParserAgent()
    llm = _get_llm()
    profiler = ResumeProfiler(llm)

    with console.status("Parsing resume..."):
        resume_data = parser.parse(file_path)

    with console.status("Profiling resume..."):
        result = profiler.profile(resume_data)

    if result.get("status") == "mcp_mode":
        console.print("[yellow]MCP mode — profiling requires an LLM provider.[/]")
        console.print("Set LLM_PROVIDER in .env (anthropic, google, or ollama)")
        return

    console.print(Panel("[bold green]Profile Extracted[/]", title="✅ Profile Complete"))
    console.print(f"  Name:     {result.get('name', 'N/A')}")
    console.print(f"  Title:    {result.get('current_title', 'N/A')}")
    console.print(f"  Years:    {result.get('experience_years', 'N/A')}")
    console.print(f"  Level:    {result.get('seniority_level', 'N/A')}")
    console.print(f"  Skills:   {', '.join(result.get('hard_skills', [])[:8])}")
    console.print(f"  Roles:    {', '.join(result.get('best_fit_roles', []))}")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        console.print(f"\n📄 Profile saved to {output}")


# ── ATS Command ──────────────────────────────────────────────

@app.command()
def ats(
    file_path: str = typer.Argument(None, help="Path to resume file. Falls back to RESUME_PATH env var."),
    job_url: Optional[str] = typer.Option(None, "--job-url", "-u", help="Job posting URL"),
    job_text: Optional[str] = typer.Option(None, "--job-text", "-t", help="Pasted JD text"),
    job_title: str = typer.Option("Unknown Role", "--title"),
    company: str = typer.Option("Unknown Company", "--company"),
):
    """Run a full ATS compatibility check against a job description."""
    file_path = _resolve_resume_path(file_path)
    if not job_url and not job_text:
        console.print("[red]Provide --job-url or --job-text[/]")
        raise typer.Exit(1)

    parser = ResumeParserAgent()
    llm = _get_llm()

    with console.status("Parsing resume..."):
        resume_data = parser.parse(file_path)

    # Get job description
    if job_url:
        fetcher = JobFetcherAgent(llm)
        with console.status("Fetching job posting..."):
            job_data = fetcher.fetch_from_url_sync(job_url)
        jd_text = job_data.get("raw_text") or job_data.get("full_description", "")
        job_title = job_data.get("title", job_title)
        company = job_data.get("company", company)
    else:
        jd_text = job_text

    with console.status("Running ATS analysis..."):
        checker = ATSCheckerAgent(llm)
        report = checker.check(resume_data, jd_text, job_title, company)

    if report.get("status") == "mcp_mode":
        console.print("[yellow]MCP mode — ATS check requires an LLM provider for Layers 2 & 3.[/]")
        console.print("Layer 1 result:")
        l1 = report.get("layer1_complete", {})
        console.print(f"  Score: {l1.get('score')}/{l1.get('max_score')}")
        return

    console.print(report.get("formatted_text", "Report generated."))


# ── Tailor Command ───────────────────────────────────────────

@app.command()
def tailor(
    file_path: str = typer.Argument(None, help="Path to resume file. Falls back to RESUME_PATH env var."),
    job_url: Optional[str] = typer.Option(None, "--job-url", "-u"),
    job_text: Optional[str] = typer.Option(None, "--job-text", "-t"),
    export: bool = typer.Option(False, "--export", help="Export tailored resume to DOCX"),
):
    """Tailor a resume for a specific job. Shows diff for confirmation."""
    file_path = _resolve_resume_path(file_path)
    if not job_url and not job_text:
        console.print("[red]Provide --job-url or --job-text[/]")
        raise typer.Exit(1)

    parser = ResumeParserAgent()
    llm = _get_llm()

    with console.status("Parsing resume..."):
        resume_data = parser.parse(file_path)

    # Get job data
    fetcher = JobFetcherAgent(llm)
    if job_url:
        job_data = fetcher.fetch_from_url_sync(job_url)
    else:
        job_data = fetcher.parse_from_text(job_text)

    with console.status("Tailoring resume..."):
        tailor_agent = TailorAgent(llm)
        result = tailor_agent.tailor(resume_data, job_data)

    if result.get("status") == "mcp_mode":
        console.print("[yellow]MCP mode — tailoring requires an LLM provider.[/]")
        return

    # Show diff
    diff = result.get("diff", {})
    console.print(Panel(
        diff.get("formatted", "No changes"),
        title=f"Resume Changes for {result.get('company', '')} — {result.get('job_title', '')}",
    ))

    # Confirmation gate
    confirmed = typer.confirm("Apply these changes?")
    if confirmed and export:
        exporter = DocExporter()
        path = exporter.export(
            result["tailored_text"],
            resume_data.get("contact"),
            job_title=result.get("job_title"),
            company=result.get("company"),
        )
        console.print(f"✅ Tailored resume exported to {path}")
    elif confirmed:
        console.print("✅ Changes approved. Use --export to save as DOCX.")
    else:
        console.print("❌ Changes discarded.")


# ── Cover Letter Command ────────────────────────────────────

@app.command(name="cover-letter")
def cover_letter(
    file_path: str = typer.Argument(None, help="Path to resume file. Falls back to RESUME_PATH env var."),
    job_url: Optional[str] = typer.Option(None, "--job-url", "-u"),
    job_text: Optional[str] = typer.Option(None, "--job-text", "-t"),
    tone: str = typer.Option("professional", "--tone", help="Tone: professional/warm/bold"),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
):
    """Generate a personalised cover letter."""
    file_path = _resolve_resume_path(file_path)
    if not job_url and not job_text:
        console.print("[red]Provide --job-url or --job-text[/]")
        raise typer.Exit(1)

    parser = ResumeParserAgent()
    llm = _get_llm()

    with console.status("Parsing resume..."):
        resume_data = parser.parse(file_path)

    fetcher = JobFetcherAgent(llm)
    if job_url:
        job_data = fetcher.fetch_from_url_sync(job_url)
    else:
        job_data = fetcher.parse_from_text(job_text)

    with console.status("Generating cover letter..."):
        agent = CoverLetterAgent(llm)
        result = agent.generate(resume_data, job_data, tone=tone)

    if result.get("status") == "mcp_mode":
        console.print("[yellow]MCP mode — cover letter requires an LLM provider.[/]")
        return

    console.print(Panel(
        result.get("cover_letter", ""),
        title=f"Cover Letter — {result.get('company', '')} {result.get('job_title', '')}",
    ))
    console.print(f"Word count: {result.get('word_count', 0)}")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result["cover_letter"])
        console.print(f"📄 Saved to {output}")


# ── Search Command ───────────────────────────────────────────

@app.command()
def search(
    query: str = typer.Argument(..., help="Job search query"),
    platforms: Optional[str] = typer.Option(None, "--platforms", "-p", help="Comma-separated platforms"),
    location: Optional[str] = typer.Option(None, "--location", "-l"),
    level: Optional[str] = typer.Option(None, "--level", help="entry/mid/senior/lead"),
    limit: int = typer.Option(10, "--limit", "-n"),
):
    """Search for jobs across platforms."""
    platform_list = platforms.split(",") if platforms else None
    agent = PlatformAgent()

    with console.status("Searching..."):
        results = asyncio.run(agent.search(
            query=query,
            platforms=platform_list,
            location=location,
            experience_level=level,
            max_per_platform=limit,
        ))

    console.print(f"\nFound {results['total_results']} results")

    for platform_name, jobs in results.get("results", {}).items():
        if jobs:
            table = Table(title=f"📋 {platform_name.title()}")
            table.add_column("Title", style="bold")
            table.add_column("Company")
            table.add_column("Location")

            for job in jobs:
                if isinstance(job, dict) and job.get("title"):
                    table.add_row(
                        job.get("title", ""),
                        job.get("company", ""),
                        job.get("location", ""),
                    )

            console.print(table)

    errors = results.get("errors", {})
    if errors:
        for plat, err in errors.items():
            console.print(f"[red]{plat}: {err}[/]")


# ── Dashboard Command ────────────────────────────────────────

@app.command()
def dashboard():
    """View the job application tracking dashboard."""
    db = Database()
    tracker = TrackerAgent(db)
    result = tracker.get_dashboard()

    console.print(result.get("formatted", "No applications tracked yet."))


# ── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    app()
