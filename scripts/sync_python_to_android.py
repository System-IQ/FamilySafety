#!/usr/bin/env python3
"""Copy backend/ + shared/contracts/ into Android python assets.

Preserves standalone files (like run_server.py) that already live
in the python/ directory.
"""
import shutil
from pathlib import Path

REPO = Path.cwd()
SRC_BACKEND = REPO / "backend"
SRC_SHARED = REPO / "shared" / "contracts"
DST_ROOT = REPO / "admin/android/app/src/main/python"

DST_ROOT.mkdir(parents=True, exist_ok=True)

# Remove only the SYNCED subdirectories, keep everything else
for sub in ("backend", "shared"):
    p = DST_ROOT / sub
    if p.exists():
        shutil.rmtree(p)

# Copy backend/
shutil.copytree(
    SRC_BACKEND,
    DST_ROOT / "backend",
    ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", "*.pyo", "data", ".pytest_cache",
    ),
)

# Copy shared/contracts/ → shared/contracts/
shutil.copytree(SRC_SHARED, DST_ROOT / "shared" / "contracts")

print(f"✓ Synced to {DST_ROOT}")
print(f"  backend files : {len(list((DST_ROOT / 'backend').rglob('*.py')))}")
print(f"  contract files: {len(list((DST_ROOT / 'shared').rglob('*.json')))}")
print(f"  standalone    : {[f.name for f in DST_ROOT.glob('*.py')]}")
