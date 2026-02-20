# Job Application Autopilot 🚀

AI-powered job application agent. Parses resumes, checks ATS compatibility, tailors content, generates cover letters, searches multiple platforms, and tracks applications — all from your AI assistant or CLI.

## ⚡ Quick Start

```bash
# Clone and install
git clone https://github.com/ViswaSrimaan/Job_Application_Autopilot_MCP.git
cd Job_Application_Autopilot_MCP
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[all]"

# Configure environment
copy .env.example .env
# Edit .env with your API keys
```

## 🔧 Usage

### As an MCP Server (Claude Code / Google Antigravity)

```jsonc
// Add to your MCP server config
{
  "mcpServers": {
    "job-autopilot": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "path/to/Job_Application_Autopilot_MCP"
    }
  }
}
```

Then ask your AI assistant:
- *"Parse my resume at resume.pdf"*
- *"Check my ATS score against this job URL"*
- *"Tailor my resume for this job posting"*
- *"Generate a cover letter"*
- *"Search for Python Developer jobs in Bangalore"*

### As a CLI

```bash
# Parse a resume
job-autopilot parse resume.pdf

# Profile extraction
job-autopilot profile resume.pdf -o profile.json

# ATS check against a job URL
job-autopilot ats resume.pdf --job-url https://linkedin.com/jobs/view/...

# Tailor resume (shows diff, requires confirmation)
job-autopilot tailor resume.pdf --job-url https://... --export

# Generate cover letter
job-autopilot cover-letter resume.pdf --job-url https://... -o cover.txt

# Search jobs across platforms
job-autopilot search "Senior Python Developer" --location "Bangalore" --level senior

# Application tracker dashboard
job-autopilot dashboard
```

## 🏗️ Architecture

```
src/
├── agents/           # High-level orchestration agents
│   ├── resume_parser.py      # PDF/DOCX → structured JSON (Docling)
│   ├── resume_profiler.py    # Skills/experience extraction (LLM)
│   ├── job_fetcher.py        # URL → structured job data
│   ├── cover_letter_agent.py # Personalised cover letters (LLM)
│   ├── ats_checker.py        # 3-layer ATS orchestrator
│   ├── tailor_agent.py       # Resume tailoring (LLM)
│   ├── diff_viewer.py        # Before/after diff viewer
│   ├── reference_agent.py    # Reference resume matching
│   ├── tracker_agent.py      # Application tracking
│   ├── apply_agent.py        # Application with confirmation gate
│   └── platform_agent.py     # Multi-platform search orchestrator
├── ats/              # ATS scoring engine
│   ├── formatter_check.py    # Layer 1: formatting & structure (20 pts)
│   ├── keyword_scorer.py     # Layer 2: keyword matching (60 pts)
│   ├── integrity_check.py    # Layer 3: data integrity (20 pts)
│   ├── jd_extractor.py       # JD → structured requirements (LLM)
│   ├── resume_extractor.py   # Resume → structured skills (LLM)
│   └── report.py             # Report formatter
├── platforms/        # Job platform integrations (Playwright)
│   ├── base.py               # Abstract platform base
│   ├── linkedin.py           # LinkedIn
│   ├── naukri.py             # Naukri
│   └── others.py             # Indeed, Cutshort, Foundit, Wellfound
├── services/         # Shared services
│   ├── docling_parser.py     # IBM Docling wrapper
│   ├── llm.py                # LLM provider abstraction
│   ├── scraper.py            # Web scraper (httpx + BS4)
│   ├── session_manager.py    # Playwright session manager
│   └── doc_exporter.py       # DOCX export (python-docx)
├── storage/          # Persistence
│   ├── schema.sql            # SQLite schema
│   └── database.py           # Database CRUD
└── tools/            # MCP tool definitions
    ├── parse_resume.py
    ├── profile_resume.py
    ├── fetch_job.py
    ├── ats_check.py
    ├── tailor_resume.py
    ├── generate_cover_letter.py
    ├── export_resume.py
    ├── search_jobs.py
    ├── track_applications.py
    └── apply_job.py
```

## 🛡️ ATS Scoring Engine

The ATS checker runs a 3-layer analysis (100 points total):

| Layer | What it checks | Points | Method |
|-------|---------------|--------|--------|
| **Layer 1** | Format & structure | 20 | Docling JSON analysis |
| **Layer 2** | Keyword relevance | 60 | LLM extraction + Python scoring |
| **Layer 3** | Data integrity | 20 | Regex + Python validation |

## 🔒 Confirmation Gates

Critical actions require explicit user confirmation:
- **Resume tailoring** — shows a diff before applying changes
- **Job applications** — shows a summary before marking as submitted

## 📋 Available MCP Tools

| Tool | Description |
|------|------------|
| `tool_parse_resume` | Parse PDF/DOCX resume via Docling |
| `tool_profile_resume` | Extract professional profile |
| `tool_fetch_job` | Fetch and parse job description |
| `tool_ats_check` | Run 3-layer ATS compatibility check |
| `tool_tailor_resume` | Tailor resume for a job ⚠️ |
| `tool_generate_cover_letter` | Generate personalised cover letter |
| `tool_export_resume` | Export to formatted DOCX |
| `tool_search_jobs` | Multi-platform job search |
| `tool_track_applications` | Application tracking dashboard |
| `tool_apply_job` | Submit application ⚠️ |

⚠️ = Requires user confirmation

## 🛡️ Guard Rails & Security

| Guard Rail | Status | Impact if Missing |
|---|---|---|
| Two-step apply gate (prepare → confirm) | ✅ Enforced | Accidental submissions |
| ATS minimum score gate | ✅ Enforced | Apply with 0/100 ATS score |
| Duplicate application prevention | ✅ UNIQUE index | Double-submit same job |
| SQL injection protection | ✅ Column whitelist | DB manipulation |
| LLM prompt injection mitigation | ✅ Content delimiters | Hostile resume hijacks LLM |
| Tailor confirmation token | ✅ Token + TTL | MCP can skip diff review |
| File type validation | ✅ Extension check | Unexpected file processing |
| File size limit | ✅ Configurable (10 MB) | DoS via large file |
| File path traversal protection | ✅ Path resolution | Arbitrary file access |
| Cookie expiry detection | ✅ Timestamp check | Silent auth failure |
| Session cookie `.gitignore` | ✅ Excluded from VCS | Credential theft |
| Cover letter review flag | ✅ `requires_review` | Unreviewed letter submitted |
| Status value validation | ✅ Whitelist | Invalid state transitions |
| SQLite connection timeout | ✅ 30s timeout | `database is locked` crash |

## 🔑 LLM Providers

Configure in `.env`:
- **Anthropic** (Claude) — `LLM_PROVIDER=anthropic`
- **Google** (Gemini) — `LLM_PROVIDER=google`
- **Ollama** (local, free) — `LLM_PROVIDER=ollama`
- **MCP mode** (no API key) — `LLM_PROVIDER=none` → prompts passed to host AI

## 📜 License

MIT