"""
Family Safety — Python entry point for Android (Chaquopy).

Phase 1.3: access-code mode. No accounts, no JWT for the Android
build. The user enters a single code once; the backend accepts it
as Bearer token.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback

_server_thread: threading.Thread | None = None
_server_started_at: float = 0.0
_last_error: str = ""
_configured: bool = False
_host: str = "127.0.0.1"
_port: int = 8000
_server_instance = None  # uvicorn.Server — used for graceful shutdown


def _log(msg: str) -> None:
    print(f"[run_server] {msg}", flush=True)


def configure(files_dir: str, cache_dir: str = "", access_code: str = "") -> str:
    """Called from Kotlin once, before start_backend.

    Sets env vars so the backend uses:
      - SQLite at files_dir/familysafety.db
      - FS_ACCESS_CODE (from the user's input)
      - a stable JWT secret (for compatibility with existing endpoints)
    """
    global _configured
    # NOTE: we deliberately use FS_ENV=android (not "production").
    # The backend refuses to start with FS_ENV=production unless
    # DATABASE_URL points to Postgres. On Android we use SQLite at
    # filesDir/familysafety.db, so "android" is the correct env here.
    os.environ["FS_ENV"] = "android"
    os.environ["FS_LOG_LEVEL"] = "INFO"

    db_path = os.path.join(files_dir, "familysafety.db")
    os.environ["FS_DB_PATH"] = db_path

    if "FS_JWT_SECRET" not in os.environ:
        os.environ["FS_JWT_SECRET"] = (
            "android-local-secret-change-me-please-32b-min-length"
        )

    if access_code:
        os.environ["FS_ACCESS_CODE"] = access_code.strip()
        _log(f"access code set ({len(access_code.strip())} chars)")
    else:
        os.environ.pop("FS_ACCESS_CODE", None)
        _log("access code cleared (dashboard-only mode)")

    _configured = True
    _log(f"configure: files_dir={files_dir} db={db_path}")
    return f"configured db={db_path}"


def hello() -> str:
    info = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "configured": _configured,
        "has_access_code": bool(os.environ.get("FS_ACCESS_CODE")),
        "server_running": is_backend_ready(timeout_s=0.1),
    }
    _log(f"hello: {info}")
    return f"Python {info['python_version']} on {info['platform']}"


def _run_uvicorn() -> None:
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
        server.install_signal_handlers = lambda: None  # type: ignore[assignment]
        global _server_instance
        _server_instance = server

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
        "has_access_code": bool(os.environ.get("FS_ACCESS_CODE")),
        "server_alive": bool(_server_thread and _server_thread.is_alive()),
        "server_ready": is_backend_ready(timeout_s=0.2),
        "started_at": _server_started_at,
        "uptime_s": round(time.time() - _server_started_at, 1) if _server_started_at else 0,
        "host": _host,
        "port": _port,
        "last_error": _last_error,
    }


def stop_backend() -> str:
    """Requests graceful shutdown of uvicorn.

    Sets server.should_exit = True; uvicorn will finish in-flight
    requests and then exit its serve() loop. The daemon thread
    terminates on its own.
    """
    global _server_instance
    if _server_instance is None:
        _log("stop_backend: no server instance")
        return "not_running"

    _log("stop_backend: requesting graceful shutdown")
    _server_instance.should_exit = True
    # Wait up to 5s for the thread to finish
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if _server_thread is None or not _server_thread.is_alive():
            _server_instance = None
            _log("stop_backend: stopped cleanly")
            return "stopped"
        time.sleep(0.1)
    _log("stop_backend: timeout (thread still alive)")
    return "timeout"
