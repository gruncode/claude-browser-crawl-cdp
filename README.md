# claude-browser-crawl-cdp

[![ci](https://github.com/gruncode/claude-browser-crawl-cdp/actions/workflows/ci.yml/badge.svg)](https://github.com/gruncode/claude-browser-crawl-cdp/actions/workflows/ci.yml)

Drive a **real, logged-in Chrome** from Claude Code (or any coding agent) over CDP — fast.

The core is a tiny **persistent Playwright REPL** (`cdp-repl` + `cdp-eval`) that
holds one live [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
connection on a Unix socket. Each call becomes a ~30 ms round-trip instead of
the ~750 ms it costs to re-spawn Python + Playwright + reconnect every time —
about **25× faster** for any multi-step automation.

It ships with an **agent reference** (`agent/web-crawl-cdp.md`) so a coding
agent like [Claude Code](https://docs.claude.com/en/docs/claude-code) can use
the toolkit correctly (display/focus handling, anti-bot patterns), plus a
human-readable [anti-bot field guide](docs/anti-bot-field-guide.md).

## What makes it different — a *real, logged-in* browser

Most automation spins up a **fresh headless browser**, which sites fingerprint
and block and which carries none of your sessions. This toolkit instead drives a
**real, persistent, logged-in browser** — a dedicated Chrome profile you sign in
to once, attached over CDP without touching your personal browser. To the site
it's just *you*, so **authenticated pages, SPAs, and most anti-bot defences just
work** — no proxies, no per-request fees. The CDP connection is kept warm by the
REPL for the 25× speedup. (For Chrome-hostile sites, the agent guide also covers
a cloned-Firefox-profile fallback that reuses an existing logged-in session.)

## Get the automation profile logged in — two ways

**A) Log in once.** Launch `chrome-cdp`, sign in to your sites in the window
that opens; the dedicated profile keeps those logins across reboots.

**B) Copy your everyday profile and drive the copy.** Skip manual logins by
copying your normal Chrome profile into the automation profile — the copy starts
already signed in to everything, while your real profile stays untouched:

```bash
# 1) close your everyday Chrome (the source profile must be unlocked)
# 2) copy it into the dedicated automation profile (CDP_PROFILE, default ~/.config/chrome-cdp)
rsync -a --delete \
  --exclude='Singleton*' --exclude='Cache/' --exclude='GPUCache/' --exclude='Code Cache/' \
  ~/.config/google-chrome/ "${CDP_PROFILE:-$HOME/.config/chrome-cdp}/"
# 3) launch — it drives the copy, already logged in to your sites
chrome-cdp &
```

*Lightweight variant* — if you only need cookies, copy just the cookie DB
(stop `chrome-cdp` first so the DB isn't mid-write):
```bash
cp ~/.config/google-chrome/Default/Cookies "${CDP_PROFILE:-$HOME/.config/chrome-cdp}/Default/Cookies"
```

**Why it works:** Chrome encrypts cookies/passwords with a key in your OS
keyring; because the copy stays on the **same machine and user**, the automation
profile decrypts them transparently. Cross-machine or cross-user copies won't
decrypt. Keep your everyday Chrome closed during a full-profile copy, and never
copy into a profile while its `chrome-cdp` is running (corrupts the live DB).

## How it compares

| Approach | Uses *your* real logins? | Anti-bot resistance | Cost | Best for |
|---|---|---|---|---|
| **This toolkit** — real Chrome + CDP | ✅ you're logged in | ★★★★★ real browser, real session | free | **authenticated** pages, SPAs, your own accounts |
| Headless Playwright / Puppeteer (fresh ctx) | ❌ none | ★★ easily fingerprinted | free | quick public-page scrapes |
| Playwright MCP / new automated browser | ❌ opens its own browser | ★★★ | free | simple interactive sessions |
| Stealth browsers (Camoufox, puppeteer-stealth) | ⚠️ only via cookie injection | ★★★★ anti-detect patches | free | hostile *public* sites |
| Proxy / scraping APIs (Bright Data, Firecrawl) | ❌ can't reach your accounts | ★★★★ cloud IPs + CAPTCHA solve | $ / quota | public anti-bot sites at scale |
| Vision-LLM UI agents (Fara-7B, Qwen-VL) | ✅ drives a real browser | n/a | GPU, slow | novel UIs with no stable selectors |

One-line trade-off: **for anything behind *your* login, a real logged-in session
wins; for anonymous bulk scraping of hostile public sites, a proxy/stealth tool
may fit better.** This toolkit is built for the former.

## Use it as an MCP server

The same capability is exposed as an **MCP server**, so AI agents (Claude Code,
Cursor, etc.) can drive your real, logged-in browser as tools — `navigate`,
`click`, `fill`, `evaluate`, `extract_all`, and more. Unlike browser MCPs that
open a *fresh* browser, this attaches to your **authenticated session**. Full
docs in [`mcp-server/`](mcp-server/):

```bash
chrome-cdp &                   # your logged-in Chrome on CDP :9222
pip install mcp playwright     # server deps (connect-only; no browser download)
# point your MCP client at:  python mcp-server/server.py   (env CDP_URL=http://127.0.0.1:9222)
```

## Requirements

| Layer | Needs |
|---|---|
| **OS** | Linux with **X11** (uses `wmctrl`/`xdotool`/`loginctl` for window & display handling) |
| **Browser** | Google Chrome or Chromium |
| **Python** | 3.10+ venv with `playwright` (`requirements.txt`) |
| **CLI tools** | `wmctrl xdotool curl rsync` (optional: `xprintidle`) |
| **Agent (optional)** | Claude Code or any agent that reads markdown skill files, to use `agent/web-crawl-cdp.md` |

> macOS / Windows / Wayland: the core REPL (`cdp-repl`/`cdp-eval`) works
> anywhere Playwright runs; only the X11 window/display helpers are Linux-specific.

## Install
```bash
git clone https://github.com/<you>/claude-browser-crawl-cdp
cd claude-browser-crawl-cdp
./install.sh                 # apt deps + venv + playwright browsers
export PATH="$PWD/bin:$PATH"  # or symlink bin/* into ~/.local/bin
cp .env.example .env          # then edit with your own values
```

## Configuration (environment variables)
| Var | Default | Meaning |
|---|---|---|
| `CDP_PORT` | `9222` | Chrome remote-debugging port |
| `CDP_PROFILE` | `~/.config/chrome-cdp` | dedicated automation profile (NOT your daily Chrome) |
| `CDP_PYTHON` | `python3` | a python that can `import playwright` (point at your venv) |
| `CHROME_BIN` | auto-detected | Chrome/Chromium binary |
| `CDP_SOCK` | `/tmp/cdp_repl.sock` | REPL control socket |

## Usage
```bash
# 1. Launch Chrome with CDP + auto-start the REPL
CDP_PYTHON=./.venv/bin/python chrome-cdp &
curl -s http://127.0.0.1:9222/json/version | head -2   # confirm it's up

# 2. Log in to your target site once in the opened window (cookies persist)

# 3. Drive it — each call is a ~30ms socket round-trip
echo 'page().goto("https://example.com")'              | cdp-eval
echo 'print(page().title())'                           | cdp-eval
echo 'wait("input[name=q]"); page().fill("input[name=q]", "hello")' | cdp-eval
```

Pre-bound names inside the REPL: `browser`, `ctx`, `page()`, `find('url-substr')`,
`wait(css, timeout=10000)`. Always prefer `wait(css)` over fixed sleeps — it
returns the moment the element is ready and avoids races.

Or connect directly from your own script:
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    page = browser.contexts[0].pages[0]
    print(page.title())
```

## Layout
```
bin/chrome-cdp            launch Chrome (CDP) + auto-start the REPL
bin/cdp-repl              persistent Playwright REPL (Unix socket server)  ⭐
bin/cdp-eval              one-line client for the REPL
agent/web-crawl-cdp.md    agent reference: methods, display/focus, anti-bot
docs/anti-bot-field-guide.md   human-readable anti-bot & resilience notes
```

## Security & ethics
- Keep all site credentials in `.env` (git-ignored) — never in code.
- The REPL executes arbitrary Python sent to a `0600` user-only socket; treat it
  as a local dev tool, not a network service.
- Automate only accounts/data you own or are authorised to access, and respect
  each site's Terms of Service and `robots.txt`.

## License
MIT — see [LICENSE](LICENSE).
