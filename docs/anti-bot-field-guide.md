# Anti-bot & resilient browser-automation field guide (2025–2026)

Practitioner notes on driving real browsers past anti-bot defences, and on
keeping a long automation run from wedging. Hard-won from production use;
generalised here with no site- or account-specific details.

## 1. Why a real, persistent browser beats a fresh headless one
Anti-bot systems score you on TLS/JA3 fingerprint, missing GPU/WebGL, canvas
hashes, and a cold cookie jar. A **dedicated but real** Chrome profile that has
logged in once already carries the signals that make traffic look human:
established cookies, a warmed cache, and a stable fingerprint. Drive *that* over
CDP rather than spinning up a blank headless context per run.

## 2. Cookie storage: Chrome vs Firefox
- **Firefox** keeps cookies in a plaintext `cookies.sqlite`. You can read the
  session cookies directly and inject them into another browser to reuse a
  login — useful for Google-OAuth-gated sites.
- **Chrome** encrypts cookies with AES-256-GCM (v10/v11 records, key in the
  OS keyring). Direct extraction needs the keyring, so cookie *injection* is
  usually easier sourced from Firefox.

Inject with Playwright `context.add_cookies([...])` or Selenium
`driver.add_cookie({...})`. For Google you typically need the full session set
(`SID, HSID, SSID, APISID, SAPISID` + their `__Secure-*` variants).

## 3. Tooling ladder (escalate only as needed)
1. **Plain CDP + real profile** — most sites, once logged in.
2. **Cloned Firefox profile, headed** — sites hostile to Chrome / needing a
   warm session.
3. **Camoufox headed with `block_webgl=True`** — heavy marketplaces; the WebGL
   block also dodges GPU-crash loops on weak integrated graphics.
4. **Residential-proxy scraping API** — last resort when IP reputation is the
   blocker.

## 4. GPU crashes on integrated graphics
Headed rendering can crash on weak/integrated GPUs. Disable acceleration:
- Chrome: `--disable-gpu`.
- Firefox: turn off `gfx.webrender.*`, `layers.acceleration`,
  `media.hardware-video-decoding`, `gfx.canvas.accelerated`,
  `layers.gpu-process` (see the agent reference for the exact prefs).

## 5. SPA navigation
Single-page apps (Angular/React) don't change route on URL set. Click the
element via JS, then walk up the parent chain until the app navigates:
```javascript
let el = targetElement;
for (let d = 0; d < 6 && el; d++) { el.click(); el = el.parentElement; }
```

## 6. Keeping long runs alive — the crash hierarchy
A single in-process Playwright loop catches only the shallow failures. Ranked by
depth, with what actually catches each:

| Layer | Failure mode | What catches it |
|---|---|---|
| 1 | Server doesn't respond | `page.goto(timeout=…)` raises → mark `unreachable` |
| 2 | Page loads but JS is slow | `wait_for_load_state` timeout → note, continue |
| 3 | `page.evaluate` hangs (busy main thread) | **no built-in timeout** — needs an external watcher |
| 4 | Watcher's `page.close()` also queues on the dead CDP socket | the node driver crashes; the loop spins at high CPU, 0 progress |
| 5 | Driver crashed | process looks alive but does nothing |

**Robust design: one OS subprocess per site.** Drive each site in its own
short-lived process and bound it with `subprocess.run(timeout=N)`, which sends
`SIGKILL` at the OS level — independent of Chrome's internal state. This catches
all five layers, where an in-process loop only catches 1–2.

Between iterations, reap orphan tabs with Chrome's
`http://127.0.0.1:<port>/json/close/<id>` HTTP endpoint: it responds even when a
tab's JS is wedged, because the browser process stays alive on the debug port.

## 7. Window management without trapping the user (Linux/X11)
- To keep the window out of the way, **minimize** it (`xdotool windowminimize`)
  or do a one-shot lower (`stack_mode=Below` via Xlib).
- **Never** set the persistent `_NET_WM_STATE_BELOW` flag
  (`wmctrl -b add,below`): it pins the window beneath everything and breaks the
  Maximize button afterwards — the user clicks Maximize and nothing appears to
  happen.
- For batch runs, a tiny watchdog that re-applies a small corner geometry only
  when the window is *maximized AND unfocused* keeps it tidy while still letting
  the user click Maximize to inspect (their click takes focus → watchdog backs
  off).

## 8. Ethics & terms of service
Automate only accounts and data you own or are authorised to access, and respect
each site's Terms of Service and `robots.txt`. These techniques are for
legitimate first-party automation (your own logins, your own data export), not
for evading access controls you don't have rights to.
