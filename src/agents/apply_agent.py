"""
Apply Agent — orchestrates the application submission workflow.

Implements the confirmation gate pattern:
1. Checks ATS minimum score (configurable)
2. Prevents duplicate applications for the same job
3. Prepares application (resume + cover letter + ATS check)
4. Shows the user everything that will be submitted
5. WAITS for explicit user confirmation before proceeding
6. Logs the action regardless of outcome
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from src.storage.database import Database

# Configurable via env — minimum ATS score required to create an application
MIN_ATS_SCORE = int(os.getenv("MIN_ATS_SCORE", "60"))


class ApplyAgent:
    """Orchestrates job application submission with confirmation gates."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db or Database()

    def prepare_application(
        self,
        resume_id: int,
        job_db_id: int,
        tailored_text: str | None = None,
        cover_letter: str | None = None,
        ats_score: int | None = None,
        ats_report: dict[str, Any] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Prepare an application for submission (requires confirmation).

        Creates an application record in "draft" status and returns
        all details for user review before confirmation.

        Args:
            force: Skip ATS minimum score check if True

        Returns:
            dict with application details and a confirmation token
        """
        # Guard rail #1 — ATS minimum score gate
        if ats_score is not None and ats_score < MIN_ATS_SCORE and not force:
            return {
                "error": f"ATS score {ats_score}/100 is below the minimum threshold ({MIN_ATS_SCORE}).",
                "suggestion": (
                    "Tailor your resume first to improve ATS compatibility, "
                    "or pass force=True to override this check."
                ),
                "ats_score": ats_score,
                "min_required": MIN_ATS_SCORE,
            }

        # Get resume and job data
        resume = self._db.get_resume(resume_id)
        if not resume:
            return {"error": f"Resume {resume_id} not found"}

        job = self._db.get_job(job_db_id)
        if not job:
            return {"error": f"Job {job_db_id} not found"}

        # Guard rail #2 — duplicate application detection
        existing = self._db.find_application(resume_id, job_db_id)
        if existing and existing["status"] not in ("cancelled",):
            return {
                "error": "An application already exists for this resume + job combination.",
                "existing_application": {
                    "app_id": existing["id"],
                    "status": existing["status"],
                    "created_at": existing["created_at"],
                },
                "suggestion": "Use the existing application or cancel it first.",
            }

        # Create application record
        app_id = self._db.create_application(
            resume_id=resume_id,
            job_id=job_db_id,
            ats_score=ats_score,
            ats_report=ats_report,
        )

        # Update with tailored content
        updates: dict[str, Any] = {}
        if tailored_text:
            updates["tailored_text"] = tailored_text
        if cover_letter:
            updates["cover_letter"] = cover_letter

        if updates:
            self._db.update_application(app_id, **updates)

        # Log the preparation action
        self._db.log_action(
            "prepare_application",
            {
                "app_id": app_id,
                "resume_name": resume.get("name"),
                "job_title": job.get("title"),
                "company": job.get("company"),
                "ats_score": ats_score,
            },
            application_id=app_id,
        )

        return {
            "application_id": app_id,
            "status": "draft",
            "requires_confirmation": True,
            "summary": {
                "candidate": resume.get("name", "Unknown"),
                "position": job.get("title", "Unknown"),
                "company": job.get("company", "Unknown"),
                "platform": job.get("platform"),
                "url": job.get("url"),
                "ats_score": ats_score,
                "has_tailored_resume": tailored_text is not None,
                "has_cover_letter": cover_letter is not None,
            },
            "confirmation_message": self._build_confirmation_message(
                resume, job, ats_score, tailored_text, cover_letter
            ),
        }

    def confirm_apply(self, app_id: int) -> dict[str, Any]:
        """
        Confirm and mark an application as submitted.

        This is the confirmation gate — only called after user approval.

        Args:
            app_id: Application ID to confirm

        Returns:
            Updated application dict
        """
        app = self._db.get_application(app_id)
        if not app:
            return {"error": f"Application {app_id} not found"}

        if app["status"] not in ("draft", "ready"):
            return {
                "error": f"Application {app_id} is in '{app['status']}' state — cannot submit",
                "suggestion": "Only 'draft' or 'ready' applications can be submitted",
            }

        # Single timestamp for the entire event
        now = datetime.now().isoformat()

        # Mark as submitted
        self._db.update_application(
            app_id,
            status="submitted",
            applied_at=now,
        )

        # Log the confirmed action
        self._db.log_action(
            "confirm_apply",
            {"app_id": app_id, "confirmed_at": now},
            application_id=app_id,
            confirmed=True,
        )

        return {
            "application_id": app_id,
            "status": "submitted",
            "applied_at": now,
            "message": "Application marked as submitted! Good luck! 🎯",
        }

    def cancel_application(self, app_id: int, reason: str = "") -> dict[str, Any]:
        """
        Cancel a draft application (user declined).

        Args:
            app_id: Application ID
            reason: Optional reason for cancellation
        """
        app = self._db.get_application(app_id)
        if not app:
            return {"error": f"Application {app_id} not found"}

        self._db.update_application(
            app_id,
            status="cancelled",
            notes=f"Cancelled: {reason}" if reason else "Cancelled by user",
        )

        self._db.log_action(
            "cancel_application",
            {"app_id": app_id, "reason": reason},
            application_id=app_id,
            confirmed=False,
        )

        return {
            "application_id": app_id,
            "status": "cancelled",
            "message": "Application cancelled. You can re-apply later.",
        }

    def _build_confirmation_message(
        self,
        resume: dict,
        job: dict,
        ats_score: int | None,
        tailored_text: str | None,
        cover_letter: str | None,
    ) -> str:
        """Build a confirmation message for user review."""
        lines = [
            "═══ Application Summary ═══",
            f"Candidate:  {resume.get('name', 'Unknown')}",
            f"Position:   {job.get('title', 'Unknown')}",
            f"Company:    {job.get('company', 'Unknown')}",
        ]

        if job.get("url"):
            lines.append(f"Job URL:    {job['url']}")

        if ats_score is not None:
            lines.append(f"ATS Score:  {ats_score}/100")

        lines.append(f"Resume:     {'✅ Tailored' if tailored_text else '📄 Original'}")
        lines.append(f"Cover Letter: {'✅ Generated' if cover_letter else '❌ Not included'}")

        lines.append("")
        lines.append("⚠️  Do you want to proceed with this application?")
        lines.append("    Reply 'yes' to confirm or 'no' to cancel.")
        lines.append("═" * 30)

        return "\n".join(lines)
