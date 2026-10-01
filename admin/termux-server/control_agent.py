#!/data/data/com.termux/files/usr/bin/python
"""
Family Safety — Control Agent.

A tiny HTTP server that lets the Admin app control the server
(start-server / stop-server) without opening Termux.

Security:
- Binds to 127.0.0.1 only (loopback).
- Requires `Authorization: Bearer <token>` on every request.
- Token is generated once and stored at ~/.fsserver/control-token (chmod 600).

Endpoints:
    POST /control/start    -> spawns start-server (up to 90s)
    POST /control/stop     -> spawns stop-server  (up to 30s)
    GET  /control/status   -> returns current state (fast)
    GET  /control/ping     -> health probe (no auth)
"""
from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ────────────────────────────────────────────────────────────
# Paths
# ────────────────────────────────────────────────────────────
HOME = Path.home()
STATE_DIR = HOME / ".fsserver"
TOKEN_FILE = STATE_DIR / "control-token"
LOCK_FILE = STATE_DIR / "control.lock"
LOG_FILE = STATE_DIR / "control.log"

PREFIX = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
START_SCRIPT = PREFIX / "bin" / "start-server"
STOP_SCRIPT = PREFIX / "bin" / "stop-server"
TAILSCALE_SOCKET = HOME / ".tailscale" / "tailscaled.sock"

HOST = "127.0.0.1"
PORT = 9999
START_TIMEOUT = 90
STOP_TIMEOUT = 30

# ────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ────────────────────────────────────────────────────────────
# ANSI stripping
# ────────────────────────────────────────────────────────────
import re as _re
_ANSI_RE = _re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ────────────────────────────────────────────────────────────
# Token
# ────────────────────────────────────────────────────────────
def ensure_token() -> str:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        try:
            tok = TOKEN_FILE.read_text().strip()
            if tok:
                return tok
        except Exception:
            pass
    tok = secrets.token_hex(32)
    TOKEN_FILE.write_text(tok)
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except Exception:
        pass
    log(f"Generated new control token ({len(tok)} chars)")
    return tok


# ────────────────────────────────────────────────────────────
# Lock (simple file-based, best-effort)
# ────────────────────────────────────────────────────────────
def is_locked() -> bool:
    return LOCK_FILE.exists()


def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        # stale lock? if older than 5 minutes, replace
        try:
            age = time.time() - LOCK_FILE.stat().st_mtime
            if age > 300:
                LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        if LOCK_FILE.exists():
            return False
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────
# Script runner
# ────────────────────────────────────────────────────────────
def run_script(script: Path, timeout: int) -> tuple[bool, str, int]:
    """Run a shell script and return (ok, output_tail, duration_ms)."""
    if not script.exists():
        return False, f"script not found: {script}", 0
    t0 = time.time()
    try:
        env = dict(os.environ)
        env["TERM"] = "dumb"
        env["NO_COLOR"] = "1"
        r = subprocess.run(
            [str(script)],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        duration = int((time.time() - t0) * 1000)
        tail = strip_ansi(r.stdout + "\n" + r.stderr)[-2000:]
        return r.returncode == 0, tail, duration
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s", int((time.time() - t0) * 1000)
    except Exception as e:
        return False, f"error: {e}", int((time.time() - t0) * 1000)


# ────────────────────────────────────────────────────────────
# Quick status
# ────────────────────────────────────────────────────────────
def check_server_status() -> dict:
    out: dict = {"running": False, "backend": False, "tailscale_ip": ""}

    # fs-api on 127.0.0.1:8000?
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", 8000))
        out["backend"] = True
    except Exception:
        pass
    finally:
        s.close()

    # tailscale IPv4
    if TAILSCALE_SOCKET.exists():
        try:
            r = subprocess.run(
                ["tailscale", f"--socket={TAILSCALE_SOCKET}", "ip", "-4"],
                capture_output=True, text=True, timeout=3,
            )
            ip = r.stdout.strip().split("\n")[0] if r.stdout.strip() else ""
            out["tailscale_ip"] = ip
        except Exception:
            pass

    out["running"] = bool(out["backend"] and out["tailscale_ip"])
    return out


# ────────────────────────────────────────────────────────────
# HTTP handler
# ────────────────────────────────────────────────────────────
TOKEN = ensure_token()


class Handler(BaseHTTPRequestHandler):
    server_version = "fs-control/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # silence default stderr logs

    def _auth(self) -> bool:
        h = self.headers.get("Authorization", "")
        if not h.startswith("Bearer "):
            return False
        try:
            return secrets.compare_digest(h[7:].strip(), TOKEN)
        except Exception:
            return False

    def _json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/control/ping":
            self._json(200, {"pong": True, "ts": time.time()})
            return
        if not self._auth():
            self._json(401, {"error": "unauthorized"})
            return
        if path == "/control/status":
            self._json(200, check_server_status())
            return
        self._json(404, {"error": "not found"})

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if not self._auth():
            self._json(401, {"error": "unauthorized"})
            return

        if path == "/control/start":
            if not acquire_lock():
                self._json(409, {"ok": False, "error": "another operation in progress"})
                return
            try:
                log("START requested")
                ok, out, dur = run_script(START_SCRIPT, START_TIMEOUT)
                log(f"START finished ok={ok} dur={dur}ms")
                self._json(200 if ok else 500, {
                    "ok": ok, "action": "start",
                    "duration_ms": dur, "output_tail": out,
                    "status": check_server_status(),
                })
            finally:
                release_lock()
            return

        if path == "/control/stop":
            if not acquire_lock():
                self._json(409, {"ok": False, "error": "another operation in progress"})
                return
            try:
                log("STOP requested")
                ok, out, dur = run_script(STOP_SCRIPT, STOP_TIMEOUT)
                log(f"STOP finished ok={ok} dur={dur}ms")
                self._json(200 if ok else 500, {
                    "ok": ok, "action": "stop",
                    "duration_ms": dur, "output_tail": out,
                    "status": check_server_status(),
                })
            finally:
                release_lock()
            return

        self._json(404, {"error": "not found"})


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────
def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"fs-control starting on {HOST}:{PORT}")
    log(f"token length: {len(TOKEN)}")
    log(f"token file: {TOKEN_FILE}")
    try:
        srv = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as e:
        log(f"FATAL: cannot bind {HOST}:{PORT}: {e}")
        return 1
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("interrupted by user")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
