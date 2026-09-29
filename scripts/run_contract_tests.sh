#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "==> Running full test suite"
python -m pytest tests/ -v --tb=short
echo ""
echo "==> All tests passed."
