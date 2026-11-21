"""Browser E2E fixtures — real HTTP server + Chromium.

Marked ``e2e`` and excluded from the default test run (CI uses
``-m "not external and not e2e"``) because it needs browser binaries.
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import Generator

import pytest
from flask import Flask
from playwright.sync_api import Page, sync_playwright
from werkzeug.serving import make_server

SCREENSHOT_DIR = Path(__file__).resolve().parents[2] / "test-results" / "screenshots"


@pytest.fixture
def server_url(app: Flask) -> Generator[str, None, None]:
    server = make_server("127.0.0.1", 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture
def capture_shot():
    """Save a full-page screenshot under test-results/screenshots/."""

    def _capture(page: Page, name: str) -> None:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT_DIR / f"{name}.png"), full_page=True)

    return _capture


@pytest.fixture
def browser_page(request: pytest.FixtureRequest) -> Generator[Page, None, None]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        js_errors: list[str] = []
        page.on("pageerror", lambda error: js_errors.append(str(error)))
        try:
            yield page
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(SCREENSHOT_DIR / f"{request.node.name}.png"), full_page=True
            )
            assert not js_errors, f"Browser JS errors: {js_errors}"
        finally:
            browser.close()
