#!/usr/bin/env python3
"""cdp-browser — an MCP server that drives a REAL, logged-in Chrome over CDP.

Unlike browser MCPs that spawn a fresh, empty browser, this **attaches over the
Chrome DevTools Protocol to an existing Chrome** you started with
`--remote-debugging-port` (see the `chrome-cdp` launcher). So an agent operates
inside your real, already-authenticated session — no re-login, your cookies, your
extensions, your anti-bot reputation.

Start a CDP Chrome first (e.g. `chrome-cdp &`), then run this server. Configure
the endpoint with the CDP_URL env var (default http://127.0.0.1:9222).
"""
import os
import json
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

CDP_URL = os.environ.get("CDP_URL", "http://127.0.0.1:9222")   # target Chrome
MAX_TEXT = int(os.environ.get("CDP_MAX_TEXT", "20000"))         # truncate big payloads

mcp = FastMCP("cdp-browser")
_S = {"pw": None, "browser": None}                              # process-lifetime handles


async def _browser():
    """Return a live CDP-connected browser, (re)connecting if needed."""
    b = _S["browser"]
    if b is None or not b.is_connected():                      # first call or dropped
        if _S["pw"] is None:                                   # start Playwright once
            _S["pw"] = await async_playwright().start()
        _S["browser"] = await _S["pw"].chromium.connect_over_cdp(CDP_URL)
    return _S["browser"]


async def _page():
    """The active tab (last opened), creating one if none exist."""
    b = await _browser()
    ctx = b.contexts[0] if b.contexts else await b.new_context()
    return ctx.pages[-1] if ctx.pages else await ctx.new_page()


@mcp.tool()
async def status() -> str:
    """Check the CDP connection and list open tabs (URL + title)."""
    b = await _browser()
    rows = []
    for ctx in b.contexts:
        for pg in ctx.pages:
            rows.append(f"- {pg.url}  |  {await pg.title()}")
    return f"Connected to {CDP_URL}\nTabs:\n" + ("\n".join(rows) or "(none)")


@mcp.tool()
async def navigate(url: str) -> str:
    """Navigate the active tab to a URL; returns the final URL and page title."""
    pg = await _page()
    await pg.goto(url, wait_until="domcontentloaded")
    return f"navigated to {pg.url} — {await pg.title()}"


@mcp.tool()
async def get_text(selector: str = "body") -> str:
    """Return the visible innerText of an element (default = whole page body)."""
    pg = await _page()
    el = await pg.query_selector(selector)
    if not el:
        return f"(no element matches {selector!r})"
    return (await el.inner_text())[:MAX_TEXT]


@mcp.tool()
async def extract_all(selector: str) -> str:
    """Return the innerText of EVERY element matching a selector, one per line."""
    pg = await _page()
    els = await pg.query_selector_all(selector)
    lines = [(await e.inner_text()).strip() for e in els]
    return ("\n".join(l for l in lines if l))[:MAX_TEXT] or f"(no matches for {selector!r})"


@mcp.tool()
async def click(selector: str) -> str:
    """Click the first element matching a CSS selector."""
    pg = await _page()
    await pg.click(selector, timeout=10000)
    return f"clicked {selector!r}"


@mcp.tool()
async def fill(selector: str, value: str) -> str:
    """Type a value into the input/textarea matching a CSS selector."""
    pg = await _page()
    await pg.fill(selector, value, timeout=10000)
    return f"filled {selector!r}"


@mcp.tool()
async def press_key(key: str) -> str:
    """Press a key on the active page, e.g. 'Enter', 'ArrowDown', 'Escape'."""
    pg = await _page()
    await pg.keyboard.press(key)
    return f"pressed {key}"


@mcp.tool()
async def wait_for(selector: str, timeout_ms: int = 10000) -> str:
    """Wait until a selector is visible (use instead of fixed sleeps)."""
    pg = await _page()
    await pg.wait_for_selector(selector, timeout=timeout_ms, state="visible")
    return f"visible: {selector!r}"


@mcp.tool()
async def evaluate(expression: str) -> str:
    """Run a JavaScript expression in the page; returns the JSON result.

    Example: evaluate("document.querySelectorAll('a').length")
    """
    pg = await _page()
    res = await pg.evaluate(expression)
    try:
        return json.dumps(res)[:MAX_TEXT]
    except TypeError:                                          # non-JSON-serialisable
        return str(res)[:MAX_TEXT]


def main():
    """Console entry point — runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
