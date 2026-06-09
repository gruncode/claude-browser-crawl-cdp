#!/usr/bin/env python3
"""End-to-end test for the cdp-browser MCP server.

Spawns the server over stdio (a real MCP client/server round-trip), points it at
a Chrome already running on CDP_URL (default http://127.0.0.1:9222), drives a
self-contained data: page through several tools, and asserts the results.

Exits non-zero on any failure so CI fails loudly.

Usage:
    # with a CDP Chrome already up on the given port:
    CDP_URL=http://127.0.0.1:9333 python mcp-server/test_client.py
"""
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "server.py")
CDP_URL = os.environ.get("CDP_URL", "http://127.0.0.1:9222")

# Self-contained page — no network needed. %23 == '#'.
PAGE = ("data:text/html,<h1>CDP MCP OK</h1><input id=q>"
        "<a href=%23>l1</a><a href=%23>l2</a>")


def check(label, got, want):
    ok = got.strip() == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (want {want!r})"))
    return ok


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=[SERVER],
        env={**os.environ, "CDP_URL": CDP_URL},
    )
    failures = 0
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            tools = sorted(t.name for t in (await s.list_tools()).tools)
            expected = ['click', 'evaluate', 'extract_all', 'fill', 'get_text',
                        'navigate', 'press_key', 'status', 'wait_for']
            failures += not check("tools list", ", ".join(tools), ", ".join(expected))

            async def call(name, args):
                return (await s.call_tool(name, args)).content[0].text

            await call("navigate", {"url": PAGE})
            failures += not check("get_text h1", await call("get_text", {"selector": "h1"}), "CDP MCP OK")
            await call("fill", {"selector": "#q", "value": "hello world"})
            failures += not check("fill round-trip",
                                  await call("evaluate", {"expression": "document.getElementById('q').value"}),
                                  '"hello world"')
            failures += not check("link count",
                                  await call("evaluate", {"expression": "document.querySelectorAll('a').length"}),
                                  "2")
            failures += not check("extract_all a", await call("extract_all", {"selector": "a"}), "l1\nl2")

    print(f"\n{'ALL TESTS PASSED' if failures == 0 else f'{failures} TEST(S) FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
