"""
Family Safety — Python entry point for Android (Chaquopy).

Phase 1.2: start uvicorn in a background thread.
Phase 1.3+: multi-profile support.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback

# Globals
_server_thread: threading.Thread | None = None
_server_started_at: float = 0.0
_last_error: str = ""
_configured: bool = False
_host: str = "127.0.0.1"
_port: int = 8000


def _log(msg: str) -> None:
    print(f"[run_server] {msg}", flush=True)


# ────────────────────────────────────────────────────────────
# Configuration — must be called BEFORE any backend import
# ────────────────────────────────────────────────────────────
def configure(files_dir: str, cache_dir: str = "") -> str:
    """
    Called from Kotlin once, before start_backend.
    Sets env vars so backend writes to a writable directory.
    """
    global _configured
    os.environ["FS_ENV"] = "production"
    os.environ["FS_LOG_LEVEL"] = "INFO"

    # Writable paths
    db_path = os.path.join(files_dir, "familysafety.db")
    os.environ["FS_DB_PATH"] = db_path

    # Stable JWT secret for this install (dev/staging only).
    # TODO Phase 4: generate a per-install secret and store in SharedPreferences.
    if "FS_JWT_SECRET" not in os.environ:
        os.environ["FS_JWT_SECRET"] = (
            "android-local-secret-change-me-please-32b-min-length"
        )

    _configured = True
    _log(f"configure: files_dir={files_dir} db={db_path}")
    return f"configured db={db_path}"


def hello() -> str:
    """Sanity check."""
    info = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "machine": os.uname().machine if hasattr(os, "uname") else "?",
        "configured": _configured,
        "server_running": is_backend_ready(),
    }
    _log(f"hello: {info}")
    return f"Python {info['python_version']} on {info['machine']}"


# ────────────────────────────────────────────────────────────
# Backend lifecycle
# ────────────────────────────────────────────────────────────
def _run_uvicorn() -> None:
    """Runs in a daemon thread. Blocks forever (or until crash)."""
    global _last_error
    try:
        import asyncio
        import uvicorn
        from backend.api.main import app

        _log("uvicorn: importing app")

        config = uvicorn.Config(
            app,
            host=_host,
            port=_port,
            log_level="info",
            access_log=False,
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        # Prevent signal handlers — they don't work in non-main threads.
        server.install_signal_handlers = lambda: None  # type: ignore[assignment]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _log(f"uvicorn: starting on {_host}:{_port}")
        loop.run_until_complete(server.serve())
        _log("uvicorn: server exited cleanly")
    except Exception as e:
        _last_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        _log(f"uvicorn FATAL: {_last_error}")


def start_backend(host: str = "127.0.0.1", port: int = 8000) -> str:
    global _server_thread, _server_started_at, _host, _port, _last_error

    if _server_thread and _server_thread.is_alive():
        return "already_running"

    if not _configured:
        return "error: configure() not called"

    _host, _port = host, port
    _last_error = ""
    _server_thread = threading.Thread(
        target=_run_uvicorn, daemon=True, name="uvicorn",
    )
    _server_thread.start()
    _server_started_at = time.time()
    return f"starting on {host}:{port}"


def is_backend_ready(timeout_s: float = 15.0) -> bool:
    """
    Quick check: TCP port is open? Returns True if we can connect.
    """
    import socket
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.4)
            s.connect((_host, _port))
            s.close()
            return True
        except Exception:
            time.sleep(0.25)
    return False


def get_status() -> dict:
    return {
        "configured": _configured,
        "server_alive": bool(_server_thread and _server_thread.is_alive()),
        "server_ready": is_backend_ready(timeout_s=0.2),
        "started_at": _server_started_at,
        "uptime_s": round(time.time() - _server_started_at, 1) if _server_started_at else 0,
        "host": _host,
        "port": _port,
        "last_error": _last_error,
    }


def stop_backend() -> str:
    """
    Graceful stop. Limited: uvicorn.Server.serve() doesn't expose
    a cancel API from another thread. We rely on:
      - daemon thread (dies with process)
      - Android killing the process (Force Stop)
    Phase 2 will store a Server instance ref for proper shutdown.
    """
    _log("stop_backend: not fully implemented (daemon thread)")
    return "not_implemented"
