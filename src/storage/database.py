"""
Database — SQLite setup, queries, and CRUD for application tracking.

Manages resumes, jobs, applications, and the action log.
Uses the schema defined in schema.sql.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class Database:
    """SQLite database for job application tracking."""

    # Frozen whitelist of columns that can be updated via update_application()
    _APPLICATION_UPDATABLE_COLUMNS = frozenset({
        "status", "ats_score", "ats_report", "tailored_text",
        "cover_letter", "applied_at", "platform", "notes",
    })

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = str(
            db_path
            or os.getenv("DB_PATH", "storage/applications.db")
        )
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Connect to the database and initialise schema if needed."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, timeout=30)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """Create tables from schema.sql if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                self._conn.executescript(f.read())
        else:
            # Inline fallback
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT, file_type TEXT, name TEXT, email TEXT,
                    phone TEXT, raw_text TEXT, parsed_json TEXT, profile_json TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE, title TEXT, company TEXT, location TEXT,
                    url TEXT, salary TEXT, raw_text TEXT, parsed_json TEXT,
                    jd_extract TEXT, platform TEXT,
                    fetched_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER, job_id INTEGER, status TEXT DEFAULT 'draft',
                    ats_score INTEGER, ats_report TEXT, tailored_text TEXT,
                    cover_letter TEXT, applied_at TEXT, platform TEXT, notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    application_id INTEGER,
                    confirmed INTEGER DEFAULT 0,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_app_resume_job
                    ON applications(resume_id, job_id)
                    WHERE status != 'cancelled';
            """)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Resume CRUD ──────────────────────────────────────────

    def save_resume(self, data: dict[str, Any]) -> int:
        """Save parsed resume data. Returns the resume ID."""
        conn = self.connect()
        contact = data.get("contact", {})
        cursor = conn.execute(
            """INSERT INTO resumes (file_path, file_type, name, email, phone, raw_text, parsed_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("file_info", {}).get("path", ""),
                data.get("file_info", {}).get("type", ""),
                contact.get("name"),
                contact.get("email"),
                contact.get("phone"),
                data.get("raw_text", ""),
                json.dumps(data, default=str),
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def update_resume_profile(self, resume_id: int, profile: dict[str, Any]) -> None:
        """Update resume profile JSON."""
        conn = self.connect()
        conn.execute(
            "UPDATE resumes SET profile_json = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(profile, default=str), resume_id),
        )
        conn.commit()

    def get_resume(self, resume_id: int) -> dict[str, Any] | None:
        """Get a resume by ID."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        return dict(row) if row else None

    def list_resumes(self) -> list[dict[str, Any]]:
        """List all saved resumes."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, file_path, name, email, created_at FROM resumes ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Job CRUD ─────────────────────────────────────────────

    def save_job(self, data: dict[str, Any]) -> int:
        """Save a job description. Returns the job DB ID."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT OR REPLACE INTO jobs
               (job_id, title, company, location, url, salary, raw_text, parsed_json, platform)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("job_id", ""),
                data.get("title"),
                data.get("company"),
                data.get("location"),
                data.get("url"),
                data.get("salary_range"),
                data.get("raw_text", ""),
                json.dumps(data, default=str),
                data.get("platform"),
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def get_job(self, job_db_id: int) -> dict[str, Any] | None:
        """Get a job by database ID."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_db_id,)).fetchone()
        return dict(row) if row else None

    def get_job_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        """Get a job by its short hash ID."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent jobs."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, job_id, title, company, platform, fetched_at FROM jobs ORDER BY fetched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Application CRUD ─────────────────────────────────────

    def create_application(
        self,
        resume_id: int,
        job_id: int,
        ats_score: int | None = None,
        ats_report: dict | None = None,
    ) -> int:
        """Create a new application. Returns the application ID."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO applications (resume_id, job_id, ats_score, ats_report)
               VALUES (?, ?, ?, ?)""",
            (
                resume_id,
                job_id,
                ats_score,
                json.dumps(ats_report, default=str) if ats_report else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def find_application(self, resume_id: int, job_id: int) -> dict[str, Any] | None:
        """Find an existing application for a resume + job pair."""
        conn = self.connect()
        row = conn.execute(
            """SELECT * FROM applications
               WHERE resume_id = ? AND job_id = ? AND status != 'cancelled'
               ORDER BY created_at DESC LIMIT 1""",
            (resume_id, job_id),
        ).fetchone()
        return dict(row) if row else None

    def update_application(self, app_id: int, **kwargs: Any) -> None:
        """Update application fields.

        Only columns in ``_APPLICATION_UPDATABLE_COLUMNS`` are accepted.
        Any other key raises ``ValueError`` to prevent injection.
        """
        conn = self.connect()

        # Reject any key not in the frozen whitelist *before* building SQL
        invalid_keys = set(kwargs.keys()) - self._APPLICATION_UPDATABLE_COLUMNS
        if invalid_keys:
            raise ValueError(
                f"Invalid update column(s): {invalid_keys}. "
                f"Allowed: {sorted(self._APPLICATION_UPDATABLE_COLUMNS)}"
            )

        updates: list[str] = []
        values: list[Any] = []
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(
                json.dumps(value, default=str) if isinstance(value, dict) else value
            )

        if updates:
            updates.append("updated_at = datetime('now')")
            values.append(app_id)
            conn.execute(
                f"UPDATE applications SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            conn.commit()

    def get_application(self, app_id: int) -> dict[str, Any] | None:
        """Get an application by ID."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return dict(row) if row else None

    def list_applications(self, status: str | None = None) -> list[dict[str, Any]]:
        """List applications, optionally filtered by status."""
        conn = self.connect()
        if status:
            rows = conn.execute(
                """SELECT a.id, j.title, j.company, a.status, a.ats_score, a.created_at
                   FROM applications a JOIN jobs j ON a.job_id = j.id
                   WHERE a.status = ? ORDER BY a.created_at DESC""",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT a.id, j.title, j.company, a.status, a.ats_score, a.created_at
                   FROM applications a JOIN jobs j ON a.job_id = j.id
                   ORDER BY a.created_at DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Action Log ───────────────────────────────────────────

    def log_action(
        self,
        action: str,
        details: dict[str, Any] | None = None,
        application_id: int | None = None,
        confirmed: bool = False,
    ) -> int:
        """Log an action for audit trail."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO action_log (action, details, application_id, confirmed)
               VALUES (?, ?, ?, ?)""",
            (
                action,
                json.dumps(details, default=str) if details else None,
                application_id,
                1 if confirmed else 0,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def get_action_log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent action log entries."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM action_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
