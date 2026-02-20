"""
Session Manager — manages Playwright browser sessions.

Handles browser lifecycle, cookie persistence, and page navigation.
Used by platform-specific scrapers for authenticated sessions.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SessionManager:
    """Manages Playwright browser sessions with cookie persistence."""

    def __init__(self, sessions_dir: str | Path | None = None) -> None:
        self._sessions_dir = Path(sessions_dir or "storage/sessions")
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def start(self, platform: str, headless: bool = True) -> Any:
        """
        Start a browser session, loading saved cookies if available.

        Args:
            platform: Platform name (used for cookie file naming)
            headless: Run browser in headless mode

        Returns:
            Playwright page object
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install job-application-autopilot[browser]"
            )

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)

        # Load cookies from previous session
        cookies = self._load_cookies(platform)
        storage_state = None
        if cookies:
            storage_state = {"cookies": cookies, "origins": []}

        self._context = await self._browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        return self._page

    async def save_session(self, platform: str) -> str:
        """
        Save the current session cookies for later reuse.

        Args:
            platform: Platform name

        Returns:
            Path to the saved cookies file
        """
        if self._context is None:
            raise RuntimeError("No active session to save")

        cookies = await self._context.cookies()
        return self._save_cookies(platform, cookies)

    async def close(self) -> None:
        """Close the browser session."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    async def login_prompt(self, platform: str, login_url: str) -> dict[str, Any]:
        """
        Open a browser for manual login and save the session after.

        This opens a VISIBLE browser window for the user to log in.
        After login, cookies are saved for future headless use.

        Args:
            platform: Platform name
            login_url: URL to navigate to for login

        Returns:
            dict with session status
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("Playwright not installed.")

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=False)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

        await self._page.goto(login_url)

        return {
            "status": "waiting_for_login",
            "platform": platform,
            "instruction": (
                f"A browser window has opened to {login_url}. "
                "Please log in manually. When done, call save_session() "
                "to save your session cookies for future use."
            ),
        }

    @property
    def page(self) -> Any:
        """Get the current page object."""
        return self._page

    def _load_cookies(self, platform: str) -> list[dict] | None:
        """Load cookies from a file, discarding expired entries.

        ⚠️ Security note: Cookie files in storage/sessions/ contain
        sensitive session tokens. They should never be committed to VCS.
        Ensure storage/sessions/ is in .gitignore.
        """
        cookie_file = self._sessions_dir / f"{platform}_cookies.json"
        if cookie_file.exists():
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                # Filter out expired cookies
                now = time.time()
                valid = [c for c in cookies if c.get("expires", float("inf")) > now]
                if not valid:
                    return None  # All cookies expired — need fresh login
                return valid
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save_cookies(self, platform: str, cookies: list[dict]) -> str:
        """Save cookies to a file."""
        cookie_file = self._sessions_dir / f"{platform}_cookies.json"
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, default=str)
        return str(cookie_file)

    def has_session(self, platform: str) -> bool:
        """Check if a saved session exists for a platform."""
        cookie_file = self._sessions_dir / f"{platform}_cookies.json"
        return cookie_file.exists()
