#!/usr/bin/env python3
"""Copy backend/ + shared/contracts/ into Android's python assets dir."""
import shutil
from pathlib import Path

REPO = Path.cwd()
SRC_BACKEND = REPO / "backend"
SRC_SHARED = REPO / "shared" / "contracts"
DST_ROOT = REPO / "admin/android/app/src/main/python"

# Clean
if DST_ROOT.exists():
    shutil.rmtree(DST_ROOT)
DST_ROOT.mkdir(parents=True)

# Copy backend/
shutil.copytree(
    SRC_BACKEND,
    DST_ROOT / "backend",
    ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", "*.pyo", "data", ".pytest_cache",
    ),
)

# Copy shared/contracts/ → shared/contracts/ (relative path preserved)
dst_shared = DST_ROOT / "shared" / "contracts"
shutil.copytree(SRC_SHARED, dst_shared)

print(f"✓ Copied to {DST_ROOT}")
for f in sorted(DST_ROOT.rglob("*.py")):
    print(f"  {f.relative_to(DST_ROOT)}")
for f in sorted(DST_ROOT.rglob("*.json")):
    print(f"  {f.relative_to(DST_ROOT)}")
