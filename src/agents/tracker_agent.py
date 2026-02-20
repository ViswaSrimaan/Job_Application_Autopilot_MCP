"""
Tracker Agent — tracks application status and history.

Provides a dashboard-like view of all applications, status updates,
and statistics across platforms.
"""

from __future__ import annotations

from typing import Any

from src.storage.database import Database


class TrackerAgent:
    """Tracks and reports on job application status."""

    def __init__(self, db: Database | None = None) -> None:
        self._db = db or Database()

    def get_dashboard(self) -> dict[str, Any]:
        """
        Get a summary dashboard of all applications.

        Returns:
            dict with counts by status, recent applications, and statistics
        """
        apps = self._db.list_applications()

        # Count by status
        status_counts: dict[str, int] = {}
        total_ats = 0
        ats_count = 0

        for app in apps:
            status = app.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

            if app.get("ats_score") is not None:
                total_ats += app["ats_score"]
                ats_count += 1

        avg_ats = round(total_ats / ats_count, 1) if ats_count > 0 else None

        return {
            "total_applications": len(apps),
            "status_breakdown": status_counts,
            "average_ats_score": avg_ats,
            "recent_applications": apps[:10],
            "formatted": self._format_dashboard(apps, status_counts, avg_ats),
        }

    def update_status(self, app_id: int, new_status: str, notes: str | None = None) -> dict[str, Any]:
        """
        Update an application's status.

        Args:
            app_id: Application ID
            new_status: New status (draft/ready/submitted/rejected/interview/offer)
            notes: Optional notes about the update

        Returns:
            Updated application dict
        """
        valid_statuses = {"draft", "ready", "submitted", "rejected", "interview", "offer", "cancelled"}
        if new_status not in valid_statuses:
            return {"error": f"Invalid status '{new_status}'. Use: {', '.join(valid_statuses)}"}

        kwargs: dict[str, Any] = {"status": new_status}
        if notes:
            kwargs["notes"] = notes

        self._db.update_application(app_id, **kwargs)
        self._db.log_action(
            "status_update",
            {"app_id": app_id, "new_status": new_status, "notes": notes},
            application_id=app_id,
        )

        return self._db.get_application(app_id) or {"error": f"Application {app_id} not found"}

    def get_application_history(self, app_id: int) -> dict[str, Any]:
        """
        Get the full history of an application.

        Returns the application details and all related action log entries.
        """
        app = self._db.get_application(app_id)
        if not app:
            return {"error": f"Application {app_id} not found"}

        conn = self._db.connect()
        rows = conn.execute(
            "SELECT * FROM action_log WHERE application_id = ? ORDER BY timestamp ASC",
            (app_id,),
        ).fetchall()

        return {
            "application": app,
            "history": [dict(r) for r in rows],
        }

    def _format_dashboard(
        self,
        apps: list[dict],
        status_counts: dict[str, int],
        avg_ats: float | None,
    ) -> str:
        """Format the dashboard as readable text."""
        lines = [
            "Job Application Tracker",
            "━" * 40,
            f"Total Applications: {len(apps)}",
        ]

        if avg_ats is not None:
            lines.append(f"Average ATS Score:  {avg_ats}")

        lines.append("")
        lines.append("Status Breakdown:")
        status_icons = {
            "draft": "📝", "ready": "✅", "submitted": "📤",
            "rejected": "❌", "interview": "🎯", "offer": "🎉",
        }

        for status, count in sorted(status_counts.items()):
            icon = status_icons.get(status, "•")
            lines.append(f"  {icon} {status.title()}: {count}")

        if apps:
            lines.append("")
            lines.append("Recent Applications:")
            for app in apps[:5]:
                title = app.get("title", "Unknown")
                company = app.get("company", "Unknown")
                status = app.get("status", "?")
                ats = app.get("ats_score", "N/A")
                lines.append(f"  • {title} @ {company} — {status} (ATS: {ats})")

        lines.append("━" * 40)
        return "\n".join(lines)
