-- Job Application Autopilot — SQLite Schema
-- Tracks resumes, jobs, applications, and ATS scores

-- Parsed resume metadata
CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL,
    file_type   TEXT NOT NULL,        -- "pdf" or "docx"
    name        TEXT,
    email       TEXT,
    phone       TEXT,
    raw_text    TEXT,                  -- Full extracted text
    parsed_json TEXT,                  -- Full parsed JSON
    profile_json TEXT,                 -- Profile from ResumeProfiler
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Job descriptions
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT UNIQUE NOT NULL,  -- Short hash ID
    title       TEXT,
    company     TEXT,
    location    TEXT,
    url         TEXT,
    salary      TEXT,
    raw_text    TEXT,                  -- Raw JD text
    parsed_json TEXT,                  -- Full parsed JSON
    jd_extract  TEXT,                  -- LLM-extracted requirements
    platform    TEXT,                  -- "linkedin", "naukri", etc.
    fetched_at  TEXT DEFAULT (datetime('now'))
);

-- Application tracking
CREATE TABLE IF NOT EXISTS applications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id   INTEGER REFERENCES resumes(id),
    job_id      INTEGER REFERENCES jobs(id),
    status      TEXT DEFAULT 'draft',  -- draft, ready, submitted, rejected, interview, offer
    ats_score   INTEGER,
    ats_report  TEXT,                  -- Full ATS report JSON
    tailored_text TEXT,                -- Tailored resume text
    cover_letter TEXT,
    applied_at  TEXT,
    platform    TEXT,
    notes       TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Session/action log
CREATE TABLE IF NOT EXISTS action_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT NOT NULL,         -- "parse", "profile", "ats_check", "tailor", "apply"
    details     TEXT,                  -- JSON details
    application_id INTEGER REFERENCES applications(id),
    confirmed   INTEGER DEFAULT 0,    -- 1 if user confirmed
    timestamp   TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_action_log_action ON action_log(action);

-- Prevent duplicate applications for the same resume + job
-- (allows re-applying after cancellation)
CREATE UNIQUE INDEX IF NOT EXISTS idx_app_resume_job
    ON applications(resume_id, job_id)
    WHERE status != 'cancelled';
