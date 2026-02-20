"""
MCP Tool: apply_job — prepare and submit a job application.
"""

from __future__ import annotations

from src.agents.apply_agent import ApplyAgent
from src.storage.database import Database


async def apply_job(
    resume_id: int,
    job_db_id: int,
    tailored_text: str | None = None,
    cover_letter: str | None = None,
    ats_score: int | None = None,
    ats_report: dict | None = None,
    confirm: bool = False,
    app_id: int | None = None,
) -> dict:
    """
    Prepare and submit a job application.

    ⚠️ CONFIRMATION REQUIRED — this tool prepares the application
    and shows a summary. The user must explicitly confirm before
    the application is marked as submitted.

    Two-step workflow:
    1. Call with resume_id + job_db_id → prepares application, returns summary
    2. Call with confirm=True + app_id → marks as submitted

    Args:
        resume_id: Database ID of the parsed resume
        job_db_id: Database ID of the job
        tailored_text: Tailored resume text (optional)
        cover_letter: Generated cover letter (optional)
        ats_score: ATS score (optional)
        ats_report: Full ATS report (optional)
        confirm: Set True to confirm a prepared application
        app_id: Application ID to confirm (required when confirm=True)

    Returns:
        Application summary (step 1) or submission confirmation (step 2)
    """
    db = Database()
    agent = ApplyAgent(db)

    if confirm:
        if not app_id:
            return {
                "error": "Confirmation requires app_id from a prior prepare step",
                "hint": "First call apply_job with resume_id + job_db_id to get an app_id, "
                        "then call again with confirm=True and that app_id.",
            }
        return agent.confirm_apply(app_id)

    return agent.prepare_application(
        resume_id=resume_id,
        job_db_id=job_db_id,
        tailored_text=tailored_text,
        cover_letter=cover_letter,
        ats_score=ats_score,
        ats_report=ats_report,
    )
