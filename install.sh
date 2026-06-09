#!/usr/bin/env bash
# install.sh — set up system deps, a Python venv, and Playwright browsers.
# Tested on Debian/Ubuntu; adjust the package manager for other distros.
set -euo pipefail

# --- system tools the X11 window/display helpers need ----------------------
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y wmctrl xdotool curl rsync python3-venv
  # optional: idle-based active-display detection
  sudo apt-get install -y xprintidle || true
else
  echo "Non-apt system: please install wmctrl xdotool curl rsync python3-venv yourself." >&2
fi

# --- Python venv + Playwright ---------------------------------------------
python3 -m venv .venv                       # local, git-ignored venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python -m playwright install chromium firefox   # download the browser binaries

# --- make the scripts runnable --------------------------------------------
chmod +x bin/chrome-cdp bin/cdp-repl bin/cdp-eval

cat <<'EOF'

Done.
  1) Add the tools to PATH:   export PATH="$PWD/bin:$PATH"
  2) Copy config:             cp .env.example .env   (then edit)
  3) Launch:                  CDP_PYTHON=./.venv/bin/python chrome-cdp &
  4) Drive it:                echo 'print(page().title())' | cdp-eval
EOF
