# 🚀 Job Application Autopilot — Project Plan

> An AI-powered agent that searches Indian job platforms based on your resume, runs ATS analysis,
> tailors your resume with user confirmation at every major step, benchmarks against open-source
> reference resumes, writes cover letters, and integrates with Claude Code & Google Antigravity via MCP.

---

## 🎯 What It Does

Load your resume → the agent analyses your skills and experience and uses that to drive job searches across Indian platforms (Naukri, LinkedIn, Indeed, CutShort, and more). For each match, it runs a full ATS check, benchmarks your resume against open-source reference resumes for that role, and proposes tailored changes. **You review every change before anything is saved.** When applying, the agent shows you the full job details and asks for your explicit approval first. Nothing is submitted without you saying yes.

No credentials are ever stored. Platform sessions use a one-time browser login (Playwright), after which a session cookie is saved locally — your password never touches the tool.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 📄 Resume Parser | Parses PDF/DOCX via **Docling** — extracts text, structure, reading order, headers/footers |
| 🎯 Resume-Based Search | Analyses your resume first, then searches for roles matching your actual skills and experience |
| 🌐 Platform Search | Searches Naukri, LinkedIn, Indeed, CutShort and more for matching roles |
| 🔍 Job Fetcher | Scrapes full job descriptions from any URL or pasted text |
| 🤖 ATS Checker | Scores your resume against 3 ATS layers: formatting, keyword match, and data integrity |
| 📚 Reference Resumes | Benchmarks your resume against open-source high-quality resumes for the same role |
| 🧠 Resume Tailor | Proposes changes with a diff view — **you approve before anything is saved** |
| 🛡️ Apply Gate | Shows full job details and asks for explicit confirmation before submitting any application |
| ✉️ Cover Letter Writer | Generates a personalised, professional cover letter |
| 📊 Application Tracker | SQLite-powered dashboard to track every application, status, and notes |
| 🔌 MCP Server | Exposes all tools so Claude Code & Antigravity can use them conversationally |
| 💻 CLI | Standalone Typer-based CLI for users without an AI assistant |

---

## 🏗️ Architecture

```
User / AI Assistant (Claude Code / Antigravity)
            │
            ▼
    ┌──────────────────┐
    │   MCP Server     │  ← FastMCP (same pattern as your laptop-assistant)
    │  (server.py)     │
    └────────┬─────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │                   Agent Layer                      │
    │  ResumeParserAgent   JobFetcherAgent               │
    │  ATSCheckerAgent     TailorAgent                   │
    │  CoverLetterAgent    TrackerAgent                  │
    │  PlatformAgent                                     │
    └────────┬──────────────────────────────────────────┘
             │
    ┌────────▼──────────────┐   ┌────────────────────────────┐
    │  Docling              │   │  LLM (Structured Output)   │
    │  Document Engine      │   │  Keyword / skill extract   │
    │  PDF/DOCX → JSON      │   │  Inferred skill detection  │
    └───────────────────────┘   │  Acronym expansion         │
             │                  │  Experience / edu parsing  │
             │                  └────────────────────────────┘
             │                            │
    ┌────────▼──────────────────────────▼─┐   ┌───────────────────────┐
    │  ATS Engine                          │   │  Storage Layer        │
    │  Layer 1: Formatting  (Docling JSON) │   │  SQLite DB            │
    │  Layer 2: Keywords    (LLM JSON)     │   │  Resume Store         │
    │  Layer 3: Integrity   (Regex+Python) │   │  Output Files         │
    └──────────────────────────────────────┘   └───────────────────────┘
```

---

## 🌐 Supported Job Platforms

### General & Professional
| Platform | Access Method | What We Use It For |
|---|---|---|
| **Naukri.com** | Playwright session (browser login once) | Search, fetch JDs, track applied |
| **LinkedIn** | Official OAuth API + Playwright fallback | Search, fetch JDs, Easy Apply |
| **Indeed India** | Public search API + scraping | Aggregate job search |
| **Foundit** (Monster) | Playwright session | White/blue collar roles |
| **Shine.com** | Playwright session | Entry to mid-level roles |

### Startup & Tech Focused
| Platform | Access Method | What We Use It For |
|---|---|---|
| **CutShort** | Public API | AI-matched startup roles |
| **Instahyre** | Playwright session | High-quality tech roles |
| **Wellfound** | Public API | Startup ecosystem |

### How Login Works (No Password Storage)
```
First run:
  Agent: "Do you have a Naukri account? I'll open a browser window —
          you log in once, and I'll save the session for future searches."
  → Playwright opens a real browser window
  → User logs in manually (password never touches the tool)
  → Session cookie saved to storage/sessions/naukri.json
  → All future searches reuse the cookie silently

Subsequent runs:
  → Tool loads saved cookie and searches directly
  → If session expires, prompts for a fresh manual login
```

---

## 🤖 ATS Checker Engine

The ATS Checker simulates how real corporate hiring software (Workday, Taleo, Greenhouse) parses and scores resumes. It runs in 3 layers.

### Layer 1 — Parsing & Formatting ("Can I Read It?")
Docling first converts the resume to a structured JSON. The formatter then checks:

| Rule | What We Check | Flag Severity |
|---|---|---|
| **File Type** | Only `.pdf` and `.docx` accepted | ❌ Hard block |
| **Multi-column Layout** | Detects columns that cause text jumbling | ⚠️ Warning |
| **Text Boxes / Frames** | Often skipped by older parsers | ⚠️ Warning |
| **Section Headers** | Must use standard names: *Experience*, *Education*, *Skills* | ⚠️ Warning |
| **Contact in Header/Footer** | Docling detects headers/footers; email/phone must be in body | ⚠️ Warning |
| **Non-standard Bullets** | Arrows, ticks, custom chars → flag for standard `•` or `-` | ℹ️ Info |
| **Obscure Fonts** | Fonts that corrupt on extraction | ℹ️ Info |

### Layer 2 — Keyword & Content ("Is It Relevant?")
The LLM first parses both the job description and the resume into structured JSON using **JSON mode / structured output**. No traditional NLP library needed.

**Step 1 — JD Extraction (LLM structured output):**
```json
{
  "required_hard_skills": ["Python", "Kafka", "Kubernetes", "gRPC"],
  "preferred_hard_skills": ["FastAPI", "Redis", "PostgreSQL"],
  "soft_skills": ["leadership", "communication"],
  "experience_required_years": 3,
  "education_required": "Bachelor's",
  "acronyms": {"AWS": "Amazon Web Services", "K8s": "Kubernetes"}
}
```

**Step 2 — Resume Skill Extraction (LLM structured output):**
```json
{
  "hard_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
  "inferred_skills": ["React (inferred from: led the frontend rewrite in React)"],
  "soft_skills": ["team lead", "mentoring"],
  "job_titles": ["Senior Software Engineer", "Backend Developer"],
  "total_experience_years": 4.5
}
```

**Step 3 — Scoring (pure Python logic, no library):**

| Rule | Logic |
|---|---|
| **Exact Keyword Match** | Hard skills matched exactly between JD extract and resume extract |
| **Contextual / Inferred Skills** | LLM flags skills inferred from bullet text (e.g., "led React rewrite" → React) |
| **Acronym Expansion** | LLM extracts both forms; checker advises including both in resume |
| **Keyword Density** | Count occurrences in resume text. Optimal: 2–3×. Flag if >5% of word count |
| **Contextual Placement Score** | Keyword in Job Title = 5pts, in Experience bullets = 3pts, in Skills list = 1pt |
| **Match Percentage** | `(matched_keywords / total_jd_keywords) × 100` |
| **Missing Keywords List** | Explicit list of JD keywords absent from resume extract |

### Layer 3 — Data Integrity ("Is It Complete?")
Contact info and date validation use **regex only** (zero dependencies). Employment gaps,
experience totals, and education level come from the LLM structured extract in Layer 2.

| Rule | Method | What We Check |
|---|---|---|
| **Contact Info — Email** | Regex | `[\w.-]+@[\w.-]+\.\w+` present in body (not header/footer per Docling) |
| **Contact Info — Phone** | Regex | Indian (`+91`, 10-digit) and international formats |
| **Date Formats** | Regex | Validates `MM/YYYY` or `Month YYYY`; flags fuzzy dates like "Winter 2023" or bare "2023" |
| **Employment Gaps** | LLM extract + Python | Calculates gaps from structured date list; flags gaps > 6 months |
| **Years of Experience** | LLM extract + Python | Sums durations from structured JSON; compares against JD requirement |
| **Education Level** | LLM extract | Degree tier (Bachelor's / Master's / PhD) identified contextually; checked against JD |

### ATS Score Output Example
```
ATS Report — Razorpay Senior Python Developer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Score:       73 / 100   ⚠️  Needs Improvement

Layer 1 — Formatting:   18 / 20
  ✅ File type: PDF (compatible)
  ✅ No multi-column layout detected
  ⚠️  Section header "Career History" → rename to "Experience"
  ⚠️  Phone number found in footer → move to body

Layer 2 — Keywords:     38 / 60
  Match: 63% (19/30 JD keywords found)
  ✅ Found: Python, FastAPI, PostgreSQL, Redis, Docker, CI/CD
  ❌ Missing: Kafka, gRPC, Kubernetes, payments domain, high-throughput
  ⚠️  "AWS" found but not "Amazon Web Services" — include both
  ⚠️  "Python" mentioned 7× — slightly high, aim for 2–3×

Layer 3 — Integrity:    17 / 20
  ✅ Email and phone present
  ✅ All dates in MM/YYYY format
  ✅ 4.5 years experience detected (JD requires 3+)
  ⚠️  6-month gap (Jun 2022–Dec 2022) — consider adding context

Recommendation: Tailor resume to fix the above before applying.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 📚 Reference Resume Library

When tailoring a resume, the tool benchmarks against open-source, high-quality reference resumes for the same role. This gives the LLM a concrete target to optimise toward — not just "make it better" but "make it closer to what a strong candidate for this role actually looks like."

### How It Works

```
1. User loads resume + fetches job (e.g., "Senior Python Developer")
2. Tool queries reference library for matching role + seniority level
3. Reference resume is parsed via Docling → structured JSON
4. TailorAgent receives: user_resume + job_description + reference_resume
5. LLM uses reference as a benchmark:
     - What sections does the reference have that yours is missing?
     - What phrasing patterns does the reference use for this role?
     - What skills are prominently featured that you also have but buried?
6. All suggestions are shown as a diff — you decide what to keep
```

### Reference Resume Sources

| Source | What's Available | How We Use It |
|---|---|---|
| [resume-dataset (GitHub)](https://github.com/florex/resume_corpus) | 2,000+ anonymised resumes across roles | Seed the local library |
| [Open Resume](https://github.com/xitanggg/open-resume) | Clean, ATS-optimised resume templates | Use as structural reference |
| [Awesome CV](https://github.com/posquit0/Awesome-CV) | LaTeX-based high-quality templates | Use as formatting benchmark |
| Community contributions | Users can contribute anonymised resumes | Crowdsourced quality over time |

### Storage
Reference resumes are stored locally in `reference_resumes/<role>/` as pre-parsed JSON — no network call at tailoring time, fully offline.

```
reference_resumes/
├── software_engineer/
│   ├── senior_python_dev_ref1.json
│   ├── senior_python_dev_ref2.json
│   └── backend_engineer_ref1.json
├── data_scientist/
│   └── data_scientist_ref1.json
├── product_manager/
│   └── ...
└── index.json    ← role → file mapping for fast lookup
```

---

## 🛡️ User Confirmation & Safety Gates

The tool **never makes irreversible changes silently.** Every significant action requires explicit user approval. There are three confirmation gates:

### Gate 1 — Resume Change Preview (before saving any tailored version)

Triggered when the tailor agent proposes changes to more than 2 bullet points, or makes structural changes (new sections, renamed headers). Shows a clear diff:

```
Resume Changes Proposed — Razorpay Senior Python Developer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SECTION HEADER
  - "Career History"
  + "Experience"

  BULLET — Software Engineer @ Acme Corp
  - "Worked on backend services using Python and handled APIs"
  + "Built high-throughput REST APIs in Python (FastAPI) processing
     2M+ daily requests, with Redis caching and PostgreSQL"

  BULLET — Software Engineer @ Acme Corp
  - "Used Docker for deployments"
  + "Containerised microservices with Docker and orchestrated with
     Kubernetes across 3 environments (dev/staging/prod)"

  NEW BULLET ADDED — Skills Section
  + "Kafka · gRPC · Payments domain · Amazon Web Services (AWS)"

  Reference benchmark: Senior Python Dev @ Fintech (open-source)
  ATS Score: 73 → 91 (+18 points)

  Apply these changes? [Yes / No / Edit manually]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Gate 2 — Job Application Confirmation (before submitting to any platform)

Triggered before clicking "Apply" on any platform. Shows the full job card:

```
Confirm Application — Razorpay
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Role:       Senior Python Developer
  Company:    Razorpay
  Location:   Bangalore (Hybrid)
  Salary:     ₹18–25 LPA
  Platform:   LinkedIn Easy Apply
  Posted:     2 days ago
  JD Summary: Payments infra team, Python/FastAPI, Kafka, K8s, 3+ yrs

  Resume:     outputs/razorpay-resume.docx  (ATS Score: 91/100)
  Cover:      outputs/razorpay-cover-letter.docx

  Ready to apply? [Yes / No / Preview resume first]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Gate 3 — Minor Tweaks (no confirmation needed)

Small changes (rewording a single bullet, adding an acronym expansion, fixing a section header) are applied silently and logged. The user can always run `show-changes --job-id 3` to review the full change history.

---

## 🛠️ Tech Stack

| Layer | Tool | Reason |
|---|---|---|
| Language | Python 3.10+ | Consistency with your other projects |
| LLM (MCP mode) | **None required** | Claude Code uses Claude; Antigravity uses Gemini — the host AI handles all language tasks |
| LLM (CLI mode) | Anthropic / Google / Ollama | Powers keyword extraction (structured JSON), NER, and all language tasks in CLI mode |
| **Document Parsing** | **`docling`** (IBM Research) | Replaces pdfplumber + python-docx; handles PDF/DOCX with layout, reading order, header/footer detection |
| **Keyword Extraction** | **LLM Structured Output** | Replaces spaCy — LLM extracts skills, acronyms, experience, and context-aware entities via JSON mode |
| **Contact / Date Validation** | **Regex** | Simple, zero-dependency pattern matching for email, phone, and date formats |
| Job Scraping | `httpx` + `BeautifulSoup4` | Lightweight, already in your mcp_servers stack |
| Browser Automation | `Playwright` | Secure session-based login to job platforms |
| Database | SQLite | Same pattern as AI-Meme-Lab's memory store |
| MCP Server | `FastMCP` | Already mastered in mcp_servers repo |
| CLI | `Typer` | Same as AI-Meme-Lab |
| Output Docs | `python-docx` | Export tailored resume and cover letter as DOCX |

### Why Docling over pdfplumber + python-docx?

| Capability | pdfplumber + python-docx | Docling |
|---|---|---|
| PDF text extraction | ✅ | ✅ |
| DOCX extraction | ✅ | ✅ |
| Reading order detection | ❌ | ✅ |
| Header/footer detection | ❌ | ✅ ← critical for ATS |
| Table structure extraction | Partial | ✅ |
| Multi-column layout detection | ❌ | ✅ ← critical for ATS |
| Output as structured JSON | ❌ | ✅ |
| LangChain / LlamaIndex ready | ❌ | ✅ |
| Scanned PDF (OCR) | ❌ | ✅ |

---

## 📁 Project Structure

```
job-application-autopilot/
├── server.py                     # MCP server entry point
├── cli.py                        # Typer CLI entry point
├── pyproject.toml
├── .env.example
│
├── src/
│   ├── agents/
│   │   ├── resume_parser.py      # Docling-powered PDF/DOCX parser → structured JSON
│   │   ├── resume_profiler.py    # Extracts skills/roles from resume to drive job search
│   │   ├── ats_checker.py        # 3-layer ATS analysis engine
│   │   ├── reference_agent.py    # Fetches & matches open-source reference resumes by role
│   │   ├── diff_viewer.py        # Generates before/after diff for user review
│   │   ├── job_fetcher.py        # Scrapes or parses job descriptions from URLs
│   │   ├── platform_agent.py     # Orchestrates search across job platforms
│   │   ├── tailor_agent.py       # LLM rewrites resume using ATS report + reference resume
│   │   ├── apply_agent.py        # Handles job application with confirmation gate
│   │   ├── cover_letter_agent.py # Generates cover letter
│   │   └── tracker_agent.py      # Manages application records
│   │
│   ├── ats/                      # ATS engine sub-modules
│   │   ├── formatter_check.py    # Layer 1: formatting & structure rules (Docling JSON)
│   │   ├── jd_extractor.py       # LLM structured output → JD skills/requirements JSON
│   │   ├── resume_extractor.py   # LLM structured output → resume skills/experience JSON
│   │   ├── keyword_scorer.py     # Layer 2: pure Python scoring logic (no NLP library)
│   │   ├── integrity_check.py    # Layer 3: regex for contact/dates + Python gap calc
│   │   └── report.py             # Formats and renders the ATS score report
│   │
│   ├── platforms/                # One file per job platform
│   │   ├── base.py               # Abstract base class for all platforms
│   │   ├── naukri.py             # Naukri.com Playwright integration
│   │   ├── linkedin.py           # LinkedIn OAuth + API integration
│   │   ├── indeed.py             # Indeed India scraper
│   │   ├── cutshort.py           # CutShort API integration
│   │   ├── foundit.py            # Foundit Playwright integration
│   │   └── wellfound.py          # Wellfound API integration
│   │
│   ├── services/
│   │   ├── llm.py                # OpenAI / Ollama client (dual provider)
│   │   ├── docling_parser.py     # Wraps Docling DocumentConverter
│   │   ├── scraper.py            # Generic job URL scraper
│   │   ├── session_manager.py    # Playwright browser sessions & cookies
│   │   └── doc_exporter.py       # Exports tailored resume + cover letter as DOCX
│   │
│   ├── storage/
│   │   ├── database.py           # SQLite setup and queries
│   │   ├── schema.sql            # resumes, jobs, applications, ats_reports tables
│   │   └── sessions/             # Saved browser session cookies (gitignored)
│   │
│   └── tools/                    # MCP tool definitions (one file per domain)
│       ├── resume_tools.py
│       ├── ats_tools.py          # check_ats, get_ats_report, get_missing_keywords
│       ├── reference_tools.py    # get_reference_resumes, show_benchmark
│       ├── diff_tools.py         # preview_changes, confirm_changes, show_history
│       ├── job_tools.py
│       ├── platform_tools.py
│       ├── application_tools.py  # apply_job (with confirmation gate)
│       └── output_tools.py
│
├── reference_resumes/            # Open-source reference resumes (pre-parsed JSON)
│   ├── software_engineer/
│   ├── data_scientist/
│   ├── product_manager/
│   ├── devops_engineer/
│   └── index.json                # role → files mapping
│
├── outputs/                      # Generated resumes, cover letters, ATS reports
├── assets/
│   └── resume.pdf                # User drops their master resume here
│
└── tests/
    ├── test_parser.py
    ├── test_ats_checker.py
    ├── test_reference_agent.py
    ├── test_diff_viewer.py
    ├── test_tailor.py
    ├── test_platforms.py
    └── test_tracker.py
```

---

## 🔌 MCP Tools (for Claude Code & Antigravity)

| Tool | Description | Example Prompt |
|---|---|---|
| `load_resume(file_path)` | Parse and store your master resume via Docling | *"Load my resume from Downloads/resume.pdf"* |
| `profile_resume()` | Extract skills/roles from resume to drive job search | *"What roles am I best suited for?"* |
| `connect_platform(name)` | Open browser for one-time login to a job platform | *"Connect my Naukri account"* |
| `list_platforms()` | Show which platforms are connected | *"Which job sites am I connected to?"* |
| `search_jobs(location, platforms?)` | Search jobs based on your resume profile | *"Find jobs for me in Bangalore"* |
| `fetch_job(url)` | Scrape and parse a single job posting | *"Fetch this job: linkedin.com/jobs/..."* |
| `check_ats(job_id)` | Run full 3-layer ATS analysis on your resume vs a job | *"ATS check my resume against job #3"* |
| `get_ats_report(job_id)` | Get the detailed ATS score report | *"Show me the full ATS report for Razorpay"* |
| `get_missing_keywords(job_id)` | Get list of keywords your resume is missing | *"What keywords am I missing for this role?"* |
| `get_reference_resumes(role)` | Fetch matching open-source reference resumes | *"Show me reference resumes for Python developer"* |
| `tailor_resume(job_id)` | Propose resume changes with diff preview — user confirms | *"Tailor my resume for job #3"* |
| `preview_changes(job_id)` | Show pending resume changes before saving | *"Show me what changes were proposed"* |
| `confirm_changes(job_id)` | Accept and save the tailored resume | *"Yes, apply those changes"* |
| `show_change_history(job_id)` | Review all changes made for a specific job | *"What did you change for the Razorpay resume?"* |
| `apply_job(job_id)` | Show job card and ask for confirmation before applying | *"Apply for job #3"* |
| `generate_cover_letter(job_id)` | Write a personalised cover letter | *"Write a cover letter for the Stripe role"* |
| `export_application(job_id)` | Export resume + cover letter as DOCX | *"Export my application for job #3"* |
| `add_application(company, role, url)` | Log a new application manually | *"I just applied to Google SWE"* |
| `update_status(app_id, status, notes)` | Update application status | *"Mark Stripe as 'Interview Scheduled'"* |
| `list_applications(status?)` | View tracked applications | *"Show me all pending applications"* |
| `get_stats()` | View application statistics | *"How many jobs have I applied to this month?"* |

---

## 💬 Example Conversations (with Claude Code / Antigravity)

**First-time platform setup:**
```
You:    "Help me start my job search"
Agent:  "Do you have accounts on any job platforms? I support Naukri, LinkedIn,
         Indeed, CutShort, Wellfound, and Foundit.
         I'll open a browser window — you log in once, and I handle the rest."
You:    "I have Naukri and LinkedIn"
Agent:  "Opening Naukri in your browser now. Log in and come back here when done."
        → [User logs in manually in browser window]
Agent:  "Naukri session saved! Opening LinkedIn now..."
        → [User logs in manually]
Agent:  "Both platforms connected. What kind of role are you looking for?"
```

**Resume-driven search + reference benchmark:**
```
You:    "Find me jobs in Bangalore"
Agent:  "Analysing your resume... Detected profile:
         → 4.5 yrs Python backend, FastAPI, PostgreSQL, Docker, some K8s
         → Best-fit roles: Senior Python Developer, Backend Engineer,
           Platform Engineer (mid-to-senior)
         Searching Naukri and LinkedIn... Found 24 relevant jobs.
         Top match: Senior Python Dev at Razorpay (₹18-25L) — 94% fit
         Want me to run an ATS check + benchmark against a reference resume?"
You:    "Yes"
Agent:  "ATS Score: 73/100 ⚠️  Missing: Kafka, gRPC, Kubernetes, payments domain
         Reference benchmark (Senior Python Dev @ Fintech):
         → Their experience bullets are 30% more achievement-oriented
         → They lead with impact metrics; yours lead with technologies
         Want to see the proposed changes?"
```

**Resume diff + user confirmation:**
```
You:    "Yes, show me the changes"
Agent:  "Here's what I'd change:

         HEADER: 'Career History' → 'Experience'

         BULLET (Acme Corp):
         - 'Worked on backend services using Python and handled APIs'
         + 'Built high-throughput REST APIs (FastAPI) processing 2M+ daily
            requests with Redis caching — reduced p99 latency by 40%'

         NEW SKILL: 'Kafka · gRPC · Amazon Web Services (AWS)'

         ATS Score after: 73 → 91 (+18)
         Apply these changes? [Yes / No / Edit manually]"
You:    "Yes"
Agent:  "Saved. Generating cover letter now..."
```

**Apply gate — explicit confirmation before submitting:**
```
You:    "Apply for the Razorpay job"
Agent:  "Confirm Application:
         ─────────────────────────────
         Role:     Senior Python Developer
         Company:  Razorpay
         Location: Bangalore (Hybrid)
         Salary:   ₹18–25 LPA
         Platform: LinkedIn Easy Apply
         Posted:   2 days ago
         Resume:   razorpay-resume.docx (ATS: 91/100)
         ─────────────────────────────
         Shall I submit this application? [Yes / No]"
You:    "Yes"
Agent:  "Application submitted. Logged to tracker."
```

**Checking your pipeline:**
```
You:    "How's my job search going?"
Agent:  "You have 12 applications tracked:
         - 4 Pending response
         - 3 Interview scheduled
         - 2 Offer received
         - 3 Rejected
         Average ATS score before tailoring: 71. After tailoring: 89."
```

---

## 🗓️ Development Roadmap

### Phase 1 — Core Engine (Days 1–3)
- [ ] Set up project structure and `pyproject.toml`
- [ ] Integrate **Docling** as the primary document parser (`docling_parser.py`)
- [ ] Build `ResumeParserAgent` — Docling → structured resume JSON
- [ ] Build `ResumeProfiler` — extract skills, experience level, and best-fit roles from resume
- [ ] Build `JobFetcherAgent` — scrape job posting or parse pasted text
- [ ] Build `CoverLetterAgent` — LLM drafts cover letter
- [ ] Set up `LLMService` with Anthropic/Google/Ollama support (no key needed in MCP mode)

### Phase 2 — ATS Checker (Days 4–6)
- [ ] `formatter_check.py` — Layer 1: file type, multi-column, headers/footers, section names, bullets (from Docling JSON)
- [ ] `jd_extractor.py` — LLM structured output prompt → extracts required skills, acronyms, experience, education from JD
- [ ] `resume_extractor.py` — LLM structured output prompt → extracts skills (including inferred), titles, dates from resume
- [ ] `keyword_scorer.py` — Layer 2: pure Python scoring logic using the two extracted JSON objects
- [ ] `integrity_check.py` — Layer 3: regex for email/phone/dates + Python gap/experience calculation
- [ ] `report.py` — formats scored output into the ATS report card
- [ ] `ATSCheckerAgent` — orchestrates all 3 layers and returns final score

### Phase 3 — Reference Resume Library (Days 7–8)
- [ ] Curate open-source reference resumes (resume_corpus, Open Resume, Awesome CV) for common roles
- [ ] Pre-parse all reference resumes via Docling → store as JSON in `reference_resumes/`
- [ ] Build `reference_agent.py` — match user's role to relevant reference resumes by title + seniority
- [ ] Build `index.json` — role keyword → reference file mapping for fast lookup
- [ ] Extend `TailorAgent` to receive reference resume as additional context

### Phase 4 — Tailor + Diff + Confirmation Gates (Days 9–10)
- [ ] `TailorAgent` — LLM receives resume JSON + ATS report + reference resume → proposes changes
- [ ] `DiffViewer` — generates clean before/after diff for every proposed change
- [ ] **Gate 1**: show diff to user, require `confirm_changes()` before saving (>2 bullet changes)
- [ ] **Gate 3**: minor changes (1–2 bullets, acronym fixes) applied silently and logged
- [ ] Re-runs ATS check after tailoring to confirm score improvement
- [ ] `DocExporter` — outputs confirmed tailored resume as clean DOCX

### Phase 5 — Storage, Tracking & Apply Gate (Days 11–12)
- [ ] SQLite schema: `resumes`, `jobs`, `applications`, `ats_reports`, `change_history` tables
- [ ] `TrackerAgent` — CRUD for application records
- [ ] `ApplyAgent` — **Gate 2**: shows full job card, requires `confirm_apply()` before submitting
- [ ] Typer CLI: `load`, `profile`, `search`, `fetch`, `check-ats`, `benchmark`, `tailor`, `preview`, `confirm`, `apply`, `track`, `stats`

### Phase 5 — Job Platform Integration (Days 9–11)
- [ ] `SessionManager` — Playwright browser launch, cookie save/load, session expiry detection
- [ ] `NaukriPlatform` — search jobs, fetch JDs via saved session
- [ ] `LinkedInPlatform` — OAuth setup + job search API
- [ ] `IndeedPlatform` — public search scraper
- [ ] `CutShortPlatform` — API integration
- [ ] `PlatformAgent` — orchestrates multi-platform search and deduplication
- [ ] CLI commands: `connect <platform>`, `search`, `platforms`

### Phase 6 — MCP Integration (Days 12–13)
- [ ] FastMCP server with all tools registered (resume, ATS, job, platform, tracker)
- [ ] Test with Claude Code (`mcp.json` config)
- [ ] Test with Google Antigravity (`mcp_config.json`)
- [ ] Add confirmation tokens for write/export operations

### Phase 7 — Polish & Publish (Day 14+)
- [ ] Write a proper `README.md` with demo GIF
- [ ] Add `.env.example` with all required keys
- [ ] Add `storage/sessions/` to `.gitignore` (never commit session cookies)
- [ ] Write tests for all modules
- [ ] GitHub release with install instructions
- [ ] Optional: Gradio/Streamlit web UI for non-CLI users

---

## ⚙️ Configuration (.env)

> **MCP users (Claude Code / Antigravity): no LLM key needed.** The host AI handles all
> language generation. Only set an LLM key if you are using the standalone CLI.

```env
# ── MCP MODE (Claude Code / Antigravity) ──────────────────────────────────────
# No LLM key required. Leave LLM_PROVIDER unset or set to "none".
LLM_PROVIDER=none

# ── CLI STANDALONE MODE — pick one ────────────────────────────────────────────

# Option 1: Anthropic (Claude) — best match for Claude Code users on CLI
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Option 2: Google Gemini — best match for Antigravity users on CLI
# LLM_PROVIDER=google
# GOOGLE_API_KEY=...
# GOOGLE_MODEL=gemini-2.0-flash

# Option 3: Ollama (free, local, no key needed)
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3

# ── Paths ──────────────────────────────────────────────────────────────────────
RESUME_PATH=assets/resume.pdf
OUTPUTS_DIR=outputs/
DB_PATH=storage/applications.db

# ── ATS Settings ───────────────────────────────────────────────────────────────
ATS_KEYWORD_DENSITY_MAX=0.05   # flag if keyword appears more than 5% of word count
ATS_EXPERIENCE_GAP_MONTHS=6    # flag employment gaps longer than this
```

---

## 🔧 Runtime Modes

### Mode 1 — Claude Code (MCP)
No LLM key needed. Claude handles all language tasks. Playwright required for job platform login.

Add to `.mcp.json` in your workspace root:
```json
{
  "mcpServers": {
    "job-autopilot": {
      "type": "stdio",
      "command": "<path-to-repo>/.venv/bin/python",
      "args": ["<path-to-repo>/server.py"]
    }
  }
}
```

**What Claude Code handles:** resume tailoring, cover letter writing, ATS suggestion summaries.
**What the MCP server handles:** Docling parsing, ATS scoring engine, SQLite tracking, Playwright sessions, file export.

---

### Mode 2 — Google Antigravity (MCP)
No LLM key needed. Gemini handles all language tasks. **Playwright is optional** — Antigravity's integrated browser can handle job platform login directly; Playwright is only needed for background/automated searches.

Add to `%USERPROFILE%\.gemini\antigravity\mcp_config.json`:
```json
{
  "mcpServers": {
    "job-autopilot": {
      "type": "stdio",
      "command": "<path-to-repo>\\.venv\\Scripts\\python.exe",
      "args": ["<path-to-repo>\\server.py"]
    }
  }
}
```

**What Antigravity handles:** resume tailoring, cover letter writing, ATS summaries, job platform browsing (via built-in browser).
**What the MCP server handles:** Docling parsing, ATS scoring engine, SQLite tracking, file export.

---

### Mode 3 — Standalone CLI
Requires an LLM key. Set `LLM_PROVIDER` in `.env` to `anthropic`, `google`, or `ollama`.
Playwright required for job platform login.

```bash
job-autopilot load assets/resume.pdf
job-autopilot search "Python developer" --location Bangalore
job-autopilot check-ats --job-id 3
job-autopilot tailor --job-id 3
job-autopilot export --job-id 3
```

---

## 🌟 What Makes This Stand Out on GitHub

- **Zero API keys for MCP users** — works out of the box with Claude Code and Antigravity; no setup friction
- **Works with both Claude Code and Google Antigravity** — first-class support for both; Antigravity users don't even need Playwright
- **Resume-driven job search** — searches based on your actual skills, not just a keyword you type
- **Reference resume benchmarking** — compares your resume against real open-source high-quality resumes for the same role
- **Full user control** — shows a diff before saving any resume changes; shows job card before submitting any application
- **Full ATS simulation** — 3-layer scoring engine: Docling for structure, LLM structured output for semantic keyword extraction, regex for contact/date validation. No traditional NLP library needed
- **Context-aware skill detection** — LLM infers skills from bullet text ("led the React rewrite" → React), something spaCy or BERT models miss entirely
- **Docling-powered parsing** — detects multi-column layouts, headers/footers, reading order — things pdfplumber misses entirely
- **Multi-platform job search** — searches Naukri, LinkedIn, Indeed, CutShort and more in one command
- **Secure login** — one-time browser login; your password never touches the tool
- **India-first** — built around the platforms Indian job seekers actually use
- **CLI fallback** — works standalone too, with Anthropic, Google, or local Ollama

---

## 📦 Dependencies

```toml
[project]
# Core — required for all modes. No NLP library needed.
dependencies = [
    "fastmcp",
    "typer",
    "httpx",
    "beautifulsoup4",
    "docling",          # IBM Research document parser (structure extraction)
    "python-docx",      # DOCX export only
    "sqlalchemy",
    "python-dotenv",
    "rich",             # pretty CLI output
]

[project.optional-dependencies]
# Install for standalone CLI with Claude / Anthropic API
anthropic = ["anthropic"]

# Install for standalone CLI with Google Gemini API
google = ["google-generativeai"]

# Install for standalone CLI with local models (free, no key, privacy-first)
ollama = ["ollama"]

# Install for job platform login (not needed for Antigravity users)
browser = ["playwright"]

# Install everything
all = ["anthropic", "google-generativeai", "ollama", "playwright"]
```

> **After install:**
> ```bash
> # Only if using job platform search without Antigravity:
> playwright install chromium
> ```
> No model downloads. No NLP library setup. That's it.

**Quick install guides:**

| You're using | Install command | LLM key needed? |
|---|---|---|
| Claude Code (MCP) | `pip install -e .` | ❌ None |
| Antigravity (MCP) | `pip install -e .` | ❌ None |
| CLI + Claude/Anthropic | `pip install -e ".[anthropic,browser]"` | ✅ Anthropic |
| CLI + Google/Gemini | `pip install -e ".[google,browser]"` | ✅ Google |
| CLI + local Ollama | `pip install -e ".[ollama,browser]"` | ❌ None (local) |

---

## 📚 Key References

- [Docling GitHub](https://github.com/docling-project/docling) — IBM Research document parser
- [Docling Docs](https://docling-project.github.io/docling/) — Full API documentation
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [Anthropic Structured Output](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs) — JSON mode for skill extraction
- [Ollama](https://ollama.com/) — Local LLM runtime for privacy-first CLI users

---

*Built by Mrityunjay · Inspired by the frustration of sending 100 resumes into the void*
