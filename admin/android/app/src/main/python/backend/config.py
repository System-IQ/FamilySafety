"""Environment-based configuration. No secrets hardcoded."""
import os
import secrets
import warnings
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

MIN_JWT_SECRET_LEN = 32


def load_jwt_secret() -> str:
    """
    Load JWT secret from env with failsafe behavior.

    - production + missing/short secret -> RuntimeError (refuse to start)
    - development/test + missing secret -> ephemeral random + loud warning
    - any env + valid env secret (>=32) -> that secret

    No default insecure value is ever baked into the source.
    """
    env_name = os.getenv("FS_ENV", "development")
    env_secret = os.getenv("FS_JWT_SECRET")

    if env_secret:
        if len(env_secret) < MIN_JWT_SECRET_LEN:
            raise RuntimeError(
                f"FS_JWT_SECRET must be at least {MIN_JWT_SECRET_LEN} "
                f"characters (got {len(env_secret)})"
            )
        return env_secret

    if env_name == "production":
        raise RuntimeError(
            "FS_JWT_SECRET is required when FS_ENV=production. "
            "Generate one with: "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    generated = secrets.token_urlsafe(48)
    warnings.warn(
        "FS_JWT_SECRET not set — using ephemeral random secret. "
        "All sessions will be invalidated on process restart. "
        "Set FS_JWT_SECRET (>=32 chars) to keep dev sessions.",
        RuntimeWarning,
        stacklevel=2,
    )
    return generated


class Settings:
    def __init__(self) -> None:
        self.environment: str = os.getenv("FS_ENV", "development")
        self.db_path: Path = Path(
            os.getenv("FS_DB_PATH", str(_REPO_ROOT / "data" / "familysafety.db"))
        )
        # Contracts — v1 (raw) and v2 (derived/events/alerts/...)
        self.contracts_v1_dir: Path = Path(
            os.getenv(
                "FS_CONTRACTS_V1_DIR",
                str(_REPO_ROOT / "shared" / "contracts" / "v1"),
            )
        )
        self.contracts_v2_dir: Path = Path(
            os.getenv(
                "FS_CONTRACTS_V2_DIR",
                str(_REPO_ROOT / "shared" / "contracts" / "v2"),
            )
        )
        # Backwards-compatible alias (points to v1)
        self.contracts_dir: Path = self.contracts_v1_dir
        # Auth
        self.jwt_secret: str = load_jwt_secret()
        # Access code (Android build). When set, replaces JWT login.
        # Clients send:  Authorization: Bearer <access_code>
        self.access_code: str = os.getenv("FS_ACCESS_CODE", "").strip()
        self.access_token_minutes: int = int(os.getenv("FS_ACCESS_MIN", "15"))
        self.refresh_token_days: int = int(os.getenv("FS_REFRESH_DAYS", "30"))
        # SMTP (email delivery for Forgot-PIN flow)
        self.smtp_host: str = os.getenv("FS_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port: int = int(os.getenv("FS_SMTP_PORT", "465"))
        self.smtp_user: str = os.getenv("FS_SMTP_USER", "").strip()
        self.smtp_pass: str = os.getenv("FS_SMTP_PASS", "").strip()
        self.smtp_from: str = os.getenv("FS_SMTP_FROM", "").strip() or self.smtp_user


settings = Settings()
