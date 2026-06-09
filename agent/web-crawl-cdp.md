# Web Automation via Chrome CDP — agent reference

Methods, anti-bot patterns, and window-handling rules for driving a real,
logged-in browser from an AI coding agent (e.g. Claude Code) on **Linux/X11**.

This file is an *agent instruction sheet*: point your agent at it when a task
needs a browser. It assumes the toolkit's three scripts are on `PATH`
(`chrome-cdp`, `cdp-repl`, `cdp-eval`) and a Python venv with Playwright.

## When to use
Use when a task needs to drive a browser: logging into a site, scraping
authenticated pages, navigating SPAs, or working around anti-bot measures.
For simple unauthenticated fetches, use a plain HTTP fetch / Firecrawl instead.

## Profile identity — keep automation separate from your daily browser
Run CDP against a **dedicated profile dir** (`$CDP_PROFILE`, default
`~/.config/chrome-cdp`), never your personal Chrome profile.

| Profile | Launcher | Attach CDP? |
|---|---|---|
| Your daily Chrome (`~/.config/google-chrome`) | your normal launcher | **NEVER** — it's your live session |
| Dedicated automation profile (`$CDP_PROFILE`) | `chrome-cdp` | ✅ this is the one to drive |

The dedicated profile is permanent: it survives reboots and stays logged in to
sites after a one-time manual login.

## Environment check (before any launch)
1. **Detect the active display first — don't assume.** On a multi-seat / VNC
   box, launching the automation window on the screen the user is working on
   interrupts them. Find the active X11 session:
```bash
loginctl list-sessions --no-legend | awk '{print $1}' | while read s; do
  loginctl show-session "$s" -p Display -p Type -p Remote -p Active 2>/dev/null \
    | paste -sd' ' | sed "s|^|session $s: |"
done
# Type=x11 Remote=no Active=yes  → the physical display the user is on now.
```
   - VNC displays often run outside `seat0` and won't show up here; if
     `/tmp/.X11-unix/X<n>` exists but the session is absent, treat it as a
     candidate the user may also be on.
   - Optional refinement (needs `xprintidle`): lowest idle ms = active screen.
   - Rule: launch on the display the user is **not** on, or ask if ambiguous.
2. If you preload jemalloc via `LD_PRELOAD`, prefix browser commands with
   `env -u LD_PRELOAD` (it can crash Chrome's zygote).
3. **Is CDP already up?** `curl -s http://127.0.0.1:9222/json/version | head -2`

## Window focus policy (never steal focus)
- The automation window MUST NEVER steal focus — the user may be working on
  the same display.
- After launch, **minimize (iconify)** the window with
  `xdotool windowminimize` — do **not** use `wmctrl -b add,below`: the
  `_NET_WM_STATE_BELOW` flag pins it under everything and silently breaks the
  Maximize button later (window maximizes but stays hidden).
- NEVER call `page.bring_to_front()`, `page.focus()`, `wmctrl -a`, or
  `xdotool windowactivate` on the automation window. Playwright clicks, JS
  eval, key events, and `goto()` all work on a background/iconified tab.
- Read-only checks (`curl /json/version`, `wmctrl -lp`) don't raise the window.

## Method selection

### 0) Chrome CDP + Playwright ⭐ best for any authenticated site
```bash
chrome-cdp &                       # launches dedicated profile + REPL on :9222
curl -s http://127.0.0.1:9222/json/version | head -2   # confirm up
```
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    page = browser.contexts[0].pages[0]
    # page.goto(url); page.query_selector(css); page.evaluate(js); page.keyboard.press(key)
```
- Set hidden fields via JS: `page.evaluate("document.querySelector('input[name=x]').value='20'")`
- Virtual-scroll lists (web mail): `page.keyboard.press("ArrowDown")` to load rows.

### 0b) Persistent CDP REPL ⚡ — use for >1 command in a row
- Check: `[ -S /tmp/cdp_repl.sock ] && echo UP || echo DOWN`
  (`chrome-cdp` autostarts it; if DOWN, run `cdp-repl` via your venv python).
- **25x faster** per call — handles stay alive across calls.
- Call: `echo 'CODE' | cdp-eval`
- Pre-bound names: `browser`, `ctx`, `page()`, `find('url-substr')`, `wait(css, timeout=10000)`
- **Always prefer `wait(css)` over fixed sleeps** — faster and race-free.
```bash
echo 'print(page().title())' | cdp-eval
echo 'wait("button[type=submit]"); page().click("button[type=submit]")' | cdp-eval
```

### A) Playwright MCP — quick interactive sessions, simple pages
- Drives a browser via accessibility snapshots. Opens its OWN browser, so it
  can't see your existing logged-in CDP tabs; you'd log in again there.

### B) Selenium + cloned Firefox profile — stealth / repeat tasks
- Clone an existing Firefox profile to a tmpdir (ignore lock files) so it
  carries real sessions; launch headed. Good when a site is hostile to Chrome.

### C) Cookie injection — Google-OAuth sites
- Firefox stores cookies in plaintext `cookies.sqlite` (Chrome encrypts with
  AES-256-GCM). Extract the session cookies from a Firefox profile and inject
  via `page.context().add_cookies()` / `driver.add_cookie()` to reuse a login.

## Firefox GPU prefs (if headed Firefox crashes on weak/integrated GPUs)
```python
for k in ["layers.acceleration.disabled"]:               opts.set_preference(k, True)
for k in ["gfx.webrender.all","gfx.webrender.enabled","media.hardware-video-decoding.enabled",
          "gfx.canvas.accelerated","layers.gpu-process.enabled"]: opts.set_preference(k, False)
```

## Anti-bot quick reference
| Site type | What tends to work |
|---|---|
| Social (DIV-based buttons) | cloned headed profile, already logged in; use `div[role=button]` or Enter |
| Google-OAuth sites | cookie injection from a Firefox profile |
| Heavy anti-bot marketplaces | Camoufox headed (`block_webgl=True`) or a residential-proxy scraping API |
| Bank / SPA portals | cloned profile, user logs in manually, extract via JS; expect ~10-min timeouts |

## Known gotchas
- Fresh Firefox profiles block cookies (ETP strict) → clone an existing one.
- SPA (Angular/React) nav: URL changes don't fire; JS-click the element, then
  walk up `parentElement` a few levels until the route changes.
- A renderer can hang on a heavy page; in-process watchers that call
  `page.close()` queue on the same dead socket. For batch work, run **one
  subprocess per site** with an OS-level `subprocess.run(timeout=N)` kill — it
  catches the failure modes a single in-process loop cannot (see
  `docs/anti-bot-field-guide.md`).
- Close orphan tabs via Chrome's `http://127.0.0.1:9222/json/close/<id>` HTTP
  API — it works even when a tab's JS is wedged, because the browser process
  itself stays responsive on the debug port.

## Credentials
Keep site logins in a git-ignored `.env` (never in this file or in code).
Load them at runtime from the environment.
