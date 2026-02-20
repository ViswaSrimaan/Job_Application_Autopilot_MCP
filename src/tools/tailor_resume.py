"""
MCP Tool: tailor_resume — generate a tailored resume for a specific job.
"""

from __future__ import annotations

import secrets
import time

from src.agents.tailor_agent import TailorAgent
from src.services.llm import LLMService

# In-memory token store: {token: {"text": ..., "expires": ...}}
_TAILOR_TOKENS: dict[str, dict] = {}
_TOKEN_TTL_SECONDS = 1800  # 30 minutes


def _cleanup_tokens() -> None:
    """Remove expired tokens."""
    now = time.time()
    expired = [k for k, v in _TAILOR_TOKENS.items() if v["expires"] < now]
    for k in expired:
        del _TAILOR_TOKENS[k]


def validate_tailor_token(token: str) -> str | None:
    """Validate and consume a tailor token. Returns tailored text or None."""
    _cleanup_tokens()
    entry = _TAILOR_TOKENS.pop(token, None)
    if entry and entry["expires"] > time.time():
        return entry["text"]
    return None


async def tailor_resume(
    resume_data: dict,
    job_data: dict,
    ats_report: dict | None = None,
) -> dict:
    """
    Generate a tailored version of the resume for a specific job.

    ⚠️ CONFIRMATION REQUIRED — shows a diff of proposed changes
    before applying. The user must confirm the modifications.

    Args:
        resume_data: Parsed resume from parse_resume tool
        job_data: Structured job from fetch_job tool
        ats_report: Optional ATS report to address specific issues

    Returns:
        Original text, tailored text, diff, and confirmation request
    """
    llm = LLMService()
    tailor = TailorAgent(llm)
    result = tailor.tailor(resume_data, job_data, ats_report=ats_report)

    # Generate a confirmation token for the tailored text
    if "tailored_text" in result and not result.get("error"):
        _cleanup_tokens()
        token = secrets.token_urlsafe(16)
        _TAILOR_TOKENS[token] = {
            "text": result["tailored_text"],
            "expires": time.time() + _TOKEN_TTL_SECONDS,
        }
        result["tailor_token"] = token
        result["token_expires_in_minutes"] = _TOKEN_TTL_SECONDS // 60

    return result
