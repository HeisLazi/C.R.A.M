"""
launcher.py — C.R.A.M: The Unbound  ·  Desktop Launcher

This is the entry point for the packaged .exe build.
It starts the FastAPI game server in a background thread, then opens a
pywebview window pointing at the local server — no browser needed.

Usage (dev):
    python launcher.py

Usage (build):
    See build_windows.bat — PyInstaller reads this file as the entry point.

Controls inside the game window:
    F11  — toggle fullscreen
    F5   — reload the page
    Alt+F4 / Cmd+Q — close
"""

import socket
import sys
import threading
import time

# ── pywebview import guard ────────────────────────────────────────────────────
try:
    import webview
except ImportError:
    print(
        "\n[CRAM Launcher] pywebview is not installed.\n"
        "Run:  pip install pywebview\n"
        "Then: python launcher.py\n"
    )
    sys.exit(1)

import uvicorn
from backend.main import app

# ── Config ────────────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8000
GAME_URL = f"http://{HOST}:{PORT}/play"

WINDOW_W = 1280   # default window width  (player can resize / F11 for fullscreen)
WINDOW_H = 800    # default window height

# ── Loading screen shown while FastAPI warms up ───────────────────────────────
LOADING_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>C.R.A.M — Loading</title></head>
<body style="
  background:#07040f;
  margin:0; padding:0;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  height:100vh;
  font-family:Georgia,serif;
">
  <div style="color:#9a70cc;font-size:42px;margin-bottom:18px;letter-spacing:4px">⚡ C.R.A.M</div>
  <div style="color:#c8a2ff;font-size:18px;margin-bottom:8px;letter-spacing:2px">THE UNBOUND</div>
  <div style="color:#3a2a5a;font-size:13px;margin-top:24px">Awakening the Drift…</div>
  <div id="dot" style="color:#5a3a9a;font-size:20px;margin-top:12px;animation:pulse 1.2s infinite">●</div>
  <style>@keyframes pulse{0%,100%{opacity:0.3}50%{opacity:1}}</style>
</body>
</html>"""


def _run_server():
    """Run the FastAPI server — called in a daemon thread."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    """Poll until the server is accepting connections or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection((host, port), timeout=0.3)
            s.close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def _on_window_shown(window):
    """Callback fired once the pywebview window is visible — load the game."""
    if _wait_for_server(HOST, PORT, timeout=15):
        window.load_url(GAME_URL)
    else:
        window.load_html(
            "<body style='background:#07040f;color:#cc6644;font-family:Georgia,serif;"
            "padding:60px;text-align:center'>"
            "<h2>⚠️ Server failed to start</h2>"
            "<p>Try closing other programs using port 8000 and restarting.</p>"
            "</body>"
        )


def main():
    # ── Start FastAPI in the background ──────────────────────────────────────
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    # ── Create the game window ────────────────────────────────────────────────
    window = webview.create_window(
        title="C.R.A.M — The Unbound",
        html=LOADING_HTML,          # shown while server warms up
        width=WINDOW_W,
        height=WINDOW_H,
        min_size=(800, 600),
        fullscreen=False,           # player can hit F11 to go fullscreen
        easy_drag=False,            # disable drag-to-move (game handles its own UI)
    )

    # Start pywebview — blocks until the window is closed
    webview.start(
        func=_on_window_shown,
        args=[window],
        debug=False,                # set True for dev tools during testing
    )


if __name__ == "__main__":
    main()
