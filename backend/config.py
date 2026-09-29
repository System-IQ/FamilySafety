"""Environment-based configuration. No secrets hardcoded."""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings:
    def __init__(self) -> None:
        self.environment: str = os.getenv("FS_ENV", "development")
        self.db_path: Path = Path(
            os.getenv("FS_DB_PATH", str(_REPO_ROOT / "data" / "familysafety.db"))
        )
        self.contracts_dir: Path = Path(
            os.getenv(
                "FS_CONTRACTS_DIR",
                str(_REPO_ROOT / "shared" / "contracts" / "v1"),
            )
        )


settings = Settings()
