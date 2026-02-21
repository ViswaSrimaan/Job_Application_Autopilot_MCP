# 🤝 Contributing to Job Application Autopilot

Thank you for your interest in contributing! This guide covers everything you need to get started and ensure your contributions are accepted smoothly.

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Getting Started](#-getting-started)
- [Development Setup](#-development-setup)
- [Project Structure](#-project-structure)
- [Contribution Workflow](#-contribution-workflow)
- [Coding Standards](#-coding-standards)
- [Adding New MCP Tools](#-adding-new-mcp-tools)
- [Working with the ATS Engine](#-working-with-the-ats-engine)
- [Adding Job Platforms](#-adding-job-platforms)
- [LLM Provider Guidelines](#-llm-provider-guidelines)
- [Security Guidelines](#-security-guidelines)
- [Testing Requirements](#-testing-requirements)
- [Commit & PR Conventions](#-commit--pr-conventions)
- [What We Accept](#-what-we-accept)
- [Need Help?](#-need-help)

---

## 📜 Code of Conduct

- Be **respectful** and **constructive** in all interactions.
- No harassment, discrimination, or toxic behavior of any kind.
- Focus feedback on the **code**, not the person.
- Help new contributors learn — we were all beginners once.

---

## 🚀 Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/Job_Application_Autopilot_MCP.git
   cd Job_Application_Autopilot_MCP
   ```
3. **Add the upstream remote** to stay in sync:
   ```bash
   git remote add upstream https://github.com/ViswaSrimaan/Job_Application_Autopilot_MCP.git
   ```

---

## 🛠️ Development Setup

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Git | Latest |
| pip | Latest |

### Install Dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install with all optional dependencies
pip install -e ".[all]"
```

### Configure Environment

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
```

Edit `.env` with your API keys. At minimum, configure one LLM provider (Anthropic, Google, Ollama, or `none` for MCP-only mode).

### Verify the Server Starts

```bash
python server.py
```

You should see the MCP server initialize without errors.

---

## 📁 Project Structure

```
Job_Application_Autopilot_MCP/
├── server.py                   # MCP server entry point
├── cli.py                      # Typer CLI entry point
├── pyproject.toml              # Project metadata & dependencies
├── .env.example                # Environment variable template
├── src/
│   ├── agents/                 # High-level orchestration agents
│   │   ├── resume_parser.py        # PDF/DOCX → structured JSON (Docling)
│   │   ├── resume_profiler.py      # Skills/experience extraction (LLM)
│   │   ├── job_fetcher.py          # URL → structured job data
│   │   ├── cover_letter_agent.py   # Personalised cover letters (LLM)
│   │   ├── ats_checker.py          # 3-layer ATS orchestrator
│   │   ├── tailor_agent.py         # Resume tailoring (LLM)
│   │   ├── diff_viewer.py          # Before/after diff viewer
│   │   ├── tracker_agent.py        # Application tracking
│   │   ├── apply_agent.py          # Application with confirmation gate
│   │   └── platform_agent.py       # Multi-platform search orchestrator
│   ├── ats/                    # ATS scoring engine (3 layers)
│   │   ├── formatter_check.py      # Layer 1: formatting & structure (20 pts)
│   │   ├── keyword_scorer.py       # Layer 2: keyword matching (60 pts)
│   │   ├── integrity_check.py      # Layer 3: data integrity (20 pts)
│   │   ├── jd_extractor.py         # JD → structured requirements (LLM)
│   │   ├── resume_extractor.py     # Resume → structured skills (LLM)
│   │   └── report.py               # Report formatter
│   ├── platforms/              # Job platform integrations (Playwright)
│   │   ├── base.py                 # Abstract platform base class
│   │   ├── linkedin.py             # LinkedIn scraper
│   │   ├── naukri.py               # Naukri scraper
│   │   └── others.py               # Indeed, Cutshort, Foundit, Wellfound
│   ├── services/               # Shared infrastructure services
│   │   ├── docling_parser.py       # IBM Docling wrapper
│   │   ├── llm.py                  # LLM provider abstraction
│   │   ├── scraper.py              # Web scraper (httpx + BS4)
│   │   ├── session_manager.py      # Playwright session manager
│   │   └── doc_exporter.py         # DOCX export (python-docx)
│   ├── storage/                # Persistence layer
│   │   ├── schema.sql              # SQLite schema
│   │   └── database.py             # Database CRUD operations
│   └── tools/                  # MCP tool definitions (thin wrappers)
│       ├── parse_resume.py
│       ├── profile_resume.py
│       ├── fetch_job.py
│       ├── ats_check.py
│       ├── tailor_resume.py
│       ├── generate_cover_letter.py
│       ├── export_resume.py
│       ├── search_jobs.py
│       ├── track_applications.py
│       └── apply_job.py
├── tests/                      # Test suite
├── reference_resumes/          # Reference resume templates
├── outputs/                    # Generated output files
└── storage/                    # SQLite database files
```

> [!IMPORTANT]
> **Do NOT modify the project structure** without prior discussion in a GitHub issue.

---

## 🔄 Contribution Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/short-bug-description
   ```

2. **Make your changes** following the coding standards below.

3. **Test** your changes thoroughly (see [Testing Requirements](#-testing-requirements)).

4. **Commit** with a clear message (see [Commit Conventions](#-commit--pr-conventions)).

5. **Push** your branch and open a Pull Request:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Fill out the PR description** explaining *what* you changed and *why*.

---

## 📐 Coding Standards

### Python Style

| Rule | Details |
|------|---------|
| **Formatting** | Follow [PEP 8](https://peps.python.org/pep-0008/). Use 4 spaces for indentation. |
| **Max line length** | 120 characters. |
| **Type hints** | **Required** on all function signatures. |
| **Docstrings** | **Required** on every public function, following Google-style format. |
| **Imports** | Group as: stdlib → third-party → local. No wildcard imports. |
| **Logging** | Use `logging.getLogger(__name__)` — **never** `print()`. |
| **Async I/O** | Use `asyncio.to_thread()` for blocking operations in async functions. |
| **Stdout** | **Never** write to `stdout` in server mode. It is reserved for MCP JSON-RPC. |

### Docstring Format

```python
def my_function(param: str, flag: bool = False) -> str:
    """Short one-line summary.

    Longer description if necessary.

    Args:
        param: Description of the parameter.
        flag: Description of the flag (default: False).

    Returns:
        Description of the return value.
    """
```

---

## 🧩 Adding New MCP Tools

### Architecture: Tool → Agent → Service

Tools in `src/tools/` are **thin wrappers** that define the MCP interface. They delegate to **agents** in `src/agents/` which contain the business logic. Agents use **services** in `src/services/` for shared infrastructure (LLM calls, web scraping, database, etc.).

```
MCP Tool (src/tools/)  →  Agent (src/agents/)  →  Service (src/services/)
     ↑ thin wrapper          ↑ business logic       ↑ reusable infra
```

> [!IMPORTANT]
> Do NOT put business logic directly in tool files. Always create or extend an agent.

### Step 1 — Create the Tool Definition

Add a new file in `src/tools/`:

```python
# src/tools/your_tool.py
from src.agents.your_agent import your_function

def register_tools(mcp):
    @mcp.tool()
    async def tool_your_feature(param: str, option: int = 10) -> str:
        """Clear description of what this tool does.

        Args:
            param: What this parameter represents.
            option: What this option controls (default: 10).
        """
        return await your_function(param, option)
```

### Step 2 — Register in `server.py`

```python
from src.tools.your_tool import register_tools as register_your_tools
register_your_tools(mcp)
```

### Step 3 — Add the Agent Logic

Create or extend the relevant agent in `src/agents/`.

### Step 4 — Update Documentation

Add your tool to the **Available MCP Tools** table in `README.md`. Mark tools requiring user confirmation with ⚠️.

---

## 📊 Working with the ATS Engine

The ATS engine (`src/ats/`) uses a 3-layer scoring system (100 points total):

| Layer | File | Points | Method |
|-------|------|--------|--------|
| Layer 1 | `formatter_check.py` | 20 | Docling JSON analysis |
| Layer 2 | `keyword_scorer.py` | 60 | LLM extraction + Python scoring |
| Layer 3 | `integrity_check.py` | 20 | Regex + Python validation |

### Rules for ATS Changes

- **Do NOT change the point distribution** without an issue discussion.
- Each layer must remain independently testable.
- LLM-dependent layers must handle provider failures gracefully.
- All scoring functions must return structured dicts, not raw text.

---

## 🌐 Adding Job Platforms

To add a new job platform (e.g., Glassdoor):

1. **Subclass** `BasePlatform` in `src/platforms/base.py`:
   ```python
   # src/platforms/glassdoor.py
   from src.platforms.base import BasePlatform

   class GlassdoorPlatform(BasePlatform):
       async def search(self, query, location, ...) -> list[dict]:
           ...
   ```

2. **Register** it in the platform agent (`src/agents/platform_agent.py`).

3. **Handle authentication** using the session manager — never hardcode credentials.

4. **Respect rate limits** — add appropriate delays between requests.

---

## 🤖 LLM Provider Guidelines

The project supports multiple LLM providers via `src/services/llm.py`:

| Provider | Config | Requires API Key |
|----------|--------|:---:|
| Anthropic (Claude) | `LLM_PROVIDER=anthropic` | ✅ |
| Google (Gemini) | `LLM_PROVIDER=google` | ✅ |
| Ollama (local) | `LLM_PROVIDER=ollama` | ❌ |
| MCP mode | `LLM_PROVIDER=none` | ❌ |

### Rules

- All LLM calls must go through `src/services/llm.py` — never call provider APIs directly.
- Always handle the `none` provider case (return prompts for the host AI to process).
- Use content delimiters in prompts to mitigate prompt injection.
- Never log full LLM responses at INFO level (may contain PII).

---

## 🛡️ Security Guidelines

> [!CAUTION]
> Security is **non-negotiable**. PRs that weaken protections will be rejected.

### Rules

1. **Confirmation gates** — All destructive/irreversible actions (apply, tailor) must use the two-step confirmation token system.
2. **File validation** — Validate file types and enforce size limits before processing.
3. **Path traversal** — Always resolve and validate file paths to prevent directory traversal.
4. **SQL injection** — Use parameterized queries only. Never interpolate user input into SQL.
5. **Credentials** — Never log, commit, or expose API keys, session cookies, or tokens.
6. **Session cookies** — Must be excluded from version control via `.gitignore`.
7. **Prompt injection** — Use content delimiters when passing user data to LLM prompts.
8. **SSRF** — Validate URLs before making HTTP requests; block internal/metadata endpoints.

---

## ✅ Testing Requirements

### Before Submitting a PR

1. **Server starts without errors:**
   ```bash
   python server.py
   ```

2. **Tests pass:**
   ```bash
   python -m pytest tests/ -v
   ```

3. **No new warnings or errors** in the output.

### When Adding Tests

- Place tests in the `tests/` directory.
- Use descriptive test names: `test_<what>_<expected_behavior>`.
- Cover both success and failure scenarios.
- Mock external services (LLM, web requests, Playwright) in tests.

---

## 💬 Commit & PR Conventions

### Branch Naming

```
feature/<short-description>      # New features
fix/<short-description>          # Bug fixes
security/<short-description>     # Security improvements
docs/<short-description>         # Documentation only
refactor/<short-description>     # Code refactoring (no behavior change)
platform/<short-description>     # New job platform integrations
```

### Commit Messages

Use the format: `type: short description`

```
feat: add Glassdoor platform integration
fix: handle empty resume sections in ATS Layer 1
security: add rate limiting to platform scrapers
docs: update tool table in README
refactor: extract shared scoring logic from ATS layers
test: add keyword scorer edge case tests
```

| Type | Use For |
|------|---------|
| `feat` | New features or tools |
| `fix` | Bug fixes |
| `security` | Security patches or hardening |
| `docs` | Documentation changes only |
| `refactor` | Restructuring without behavior change |
| `test` | Adding or updating tests |
| `chore` | Build, config, or dependency updates |
| `platform` | New job platform integrations |

### Pull Request Checklist

Before requesting a review, confirm:

- [ ] My code follows the coding standards above.
- [ ] I've added type hints and docstrings to all new functions.
- [ ] Business logic is in agents, not in tool files.
- [ ] Destructive operations use the confirmation token system.
- [ ] I've added/updated tests for my changes.
- [ ] All existing tests pass.
- [ ] I've updated `README.md` if I added or changed tools.
- [ ] I've tested the server starts successfully.
- [ ] My branch is up to date with `main`.
- [ ] No API keys, tokens, or credentials are committed.

---

## 🎯 What We Accept

### ✅ Welcome

- New MCP tools following the Tool → Agent → Service architecture.
- New job platform integrations.
- ATS engine improvements with clear scoring rationale.
- LLM provider additions.
- Bug fixes with clear reproduction steps.
- Documentation improvements.
- Performance optimizations.
- Security hardening.

### ❌ Will Be Rejected

- Changes that bypass or weaken security protections.
- Business logic placed directly in tool files.
- Code without type hints or docstrings.
- Hardcoded credentials or API keys.
- Large changes without a prior issue discussion.
- Breaking changes to the MCP tool API without an issue.
- Direct provider API calls bypassing `src/services/llm.py`.

---

## ❓ Need Help?

- **Found a bug?** [Open an issue](https://github.com/ViswaSrimaan/Job_Application_Autopilot_MCP/issues/new) with steps to reproduce.
- **Have a feature idea?** Open an issue to discuss it before coding.
- **Questions?** Start a discussion on the repository.

---

Thank you for contributing! Every improvement — big or small — makes this project better for everyone. ⭐
