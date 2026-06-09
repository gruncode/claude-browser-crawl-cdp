# cdp-browser — MCP server

An [MCP](https://modelcontextprotocol.io) server that lets an AI agent drive a
**real, logged-in Chrome** over the DevTools Protocol.

**The difference:** Playwright-MCP and chrome-devtools-mcp launch a *fresh, empty*
browser. This one **attaches to a Chrome you're already signed into** (started via
the `chrome-cdp` launcher), so the agent works inside your real session — your
cookies, your logins, your anti-bot reputation. Point it at authenticated pages
and SPAs and they just work, with no re-login.

## Tools
`navigate` · `get_text` · `extract_all` · `click` · `fill` · `press_key` ·
`wait_for` · `evaluate` · `status`

## Setup
```bash
pip install -r mcp-server/requirements.txt   # mcp + playwright (connect-only; no browser download)
chrome-cdp &                                  # start your logged-in Chrome on CDP :9222
```

## Add to an MCP client (e.g. Claude Code)
```json
{
  "mcpServers": {
    "cdp-browser": {
      "command": "python",
      "args": ["/abs/path/to/claude-browser-crawl-cdp/mcp-server/server.py"],
      "env": { "CDP_URL": "http://127.0.0.1:9222" }
    }
  }
}
```
Use the Python that has `mcp` + `playwright` installed (e.g. your venv's
`bin/python`).

## Config (env)
| Var | Default | Meaning |
|---|---|---|
| `CDP_URL` | `http://127.0.0.1:9222` | CDP endpoint of the running Chrome |
| `CDP_MAX_TEXT` | `20000` | max characters returned by text tools |

## Test
With a CDP Chrome running on the port you pass:
```bash
CDP_URL=http://127.0.0.1:9333 python mcp-server/test_client.py
```
The same test runs in CI on every push (see `.github/workflows/ci.yml`).

## Security
The server runs `evaluate` (arbitrary JS) and drives a browser holding your real
sessions — run it locally, for your own accounts, and review what an agent does
with it. It opens no network ports of its own (stdio transport).
