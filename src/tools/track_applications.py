"""
MCP Tool: track_applications — view and manage application status.
"""

from __future__ import annotations

from src.agents.tracker_agent import TrackerAgent
from src.storage.database import Database


async def track_applications(
    action: str = "dashboard",
    app_id: int | None = None,
    new_status: str | None = None,
    notes: str | None = None,
) -> dict:
    """
    View and manage job application tracking.

    Actions:
    - "dashboard" — see all applications with status breakdown
    - "update" — update an application's status (requires app_id + new_status)
    - "history" — view full history of an application (requires app_id)
    - "list" — list all applications

    Args:
        action: Action to perform — "dashboard", "update", "history", "list"
        app_id: Application ID (required for update/history)
        new_status: New status — draft/ready/submitted/rejected/interview/offer
        notes: Optional notes for status update

    Returns:
        Dashboard data, application list, or updated application
    """
    db = Database()
    tracker = TrackerAgent(db)

    if action == "dashboard":
        return tracker.get_dashboard()
    elif action == "update":
        if not app_id or not new_status:
            return {"error": "app_id and new_status are required for update"}
        return tracker.update_status(app_id, new_status, notes)
    elif action == "history":
        if not app_id:
            return {"error": "app_id is required for history"}
        return tracker.get_application_history(app_id)
    elif action == "list":
        return {"applications": db.list_applications(status=new_status)}
    else:
        return {"error": f"Unknown action: {action}. Use: dashboard, update, history, list"}
