"""Startup validation and informational banner.

Runs ONCE at app import time. Refuses to start if production
requirements are not met (fail fast).
"""
import logging
import os
import platform
import sys

from .config import settings

logger = logging.getLogger("familysafety.startup")


def validate_startup() -> None:
    """Refuse to start with an insecure production config."""
    env = settings.environment
    errors: list[str] = []
    warnings: list[str] = []

    # --- JWT secret (skipped when access-code mode is active) ---
    if not settings.access_code:
        secret = settings.jwt_secret
        if env == "production":
            if len(secret) < 32:
                errors.append("JWT secret must be >= 32 chars in production")
            if "insecure" in secret.lower() or "changeme" in secret.lower():
                errors.append("JWT secret contains an obviously weak value")

    # --- Database ---
    if env == "production" and os.getenv("DATABASE_URL", "").strip() == "":
        errors.append(
            "DATABASE_URL is required in production "
            "(SQLite is dev-only; Render provides PostgreSQL)"
        )

    # --- Warnings (not fatal) ---
    if env != "production" and "insecure" in secret.lower():
        warnings.append("Using development JWT secret — fine for dev only")

    if warnings:
        for w in warnings:
            logger.warning("STARTUP WARNING: %s", w)

    if errors:
        for e in errors:
            logger.error("STARTUP ERROR: %s", e)
        raise RuntimeError(
            "Refusing to start — fix the above errors:\n  " + "\n  ".join(errors)
        )


def log_banner() -> None:
    """Log a concise startup banner."""
    from .db import db_backend, ping
    ok, err, latency = ping()
    logger.info("=" * 62)
    logger.info("Family Safety API")
    logger.info("  environment : %s", settings.environment)
    logger.info("  python      : %s", platform.python_version())
    logger.info("  platform    : %s %s", platform.system(), platform.machine())
    logger.info("  database    : %s", db_backend())
    logger.info("  db ping     : %s (%.2f ms)",
                "OK" if ok else f"FAIL ({err})", latency)
    logger.info("  access mins : %d", settings.access_token_minutes)
    logger.info("  refresh days: %d", settings.refresh_token_days)
    logger.info("=" * 62)


def configure_logging() -> None:
    """JSON-ish structured logging. Reads FS_LOG_LEVEL (default INFO)."""
    level_name = os.getenv("FS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    if root.handlers:
        # already configured (e.g., by tests)
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt='{"ts":"%(asctime)s","lvl":"%(levelname)s",'
            '"logger":"%(name)s","msg":%(message)s}',
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    ))
    root.addHandler(handler)
    root.setLevel(level)
