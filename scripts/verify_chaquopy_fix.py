#!/usr/bin/env python3
"""
Verify Chaquopy fix: no version pins + cross-refs intact.

Focus: catch the CI failure cause (pydantic-core Rust) and confirm
nothing else regressed.
"""
import re
import sys
from pathlib import Path

REPO = Path.cwd()
APP_GRADLE = REPO / "admin/android/app/build.gradle.kts"
ROOT_GRADLE = REPO / "admin/android/build.gradle.kts"

errors: list[str] = []
warnings: list[str] = []
passed = 0


def ok(m: str) -> None:
    global passed
    passed += 1
    print(f"  ✅ {m}")


def err(m: str) -> None:
    errors.append(m)
    print(f"  ❌ {m}")


def warn(m: str) -> None:
    warnings.append(m)
    print(f"  ⚠️  {m}")


def section(t: str) -> None:
    print()
    print("═" * 66)
    print(f"  {t}")
    print("═" * 66)


# ════════════════════════════════════════════════════════════
# 1. chaquopy block — no version pins
# ════════════════════════════════════════════════════════════
section("1. Chaquopy block — no version pins")

src = APP_GRADLE.read_text()
m = re.search(r'chaquopy\s*\{([\s\S]*?)\n\}', src)
if not m:
    err("chaquopy block not found")
else:
    body = m.group(1)

    # Should have install(...) lines
    installs = re.findall(r'install\("([^"]+)"\)', body)
    if not installs:
        err("no install() calls found in chaquopy")
    else:
        ok(f"{len(installs)} install() calls")

    # NO version pins
    pinned = re.findall(r'install\("([^"]+==[^"]+)"\)', body)
    if pinned:
        for pkg in pinned:
            err(f"version pin still present: {pkg}")
    else:
        ok("no version pins (good)")

    # Expected packages present (without versions)
    expected = {"fastapi", "uvicorn", "pyjwt", "jsonschema", "rfc3339-validator"}
    found = set(installs)
    missing = expected - found
    if missing:
        for pkg in missing:
            err(f"missing package: {pkg}")
    else:
        ok(f"all required packages: {sorted(expected)}")

    # pydantic NOT pinned explicitly
    if "pydantic" in body and "install(\"pydantic" in body:
        warn("pydantic explicitly installed (may cause version conflict)")
    else:
        ok("pydantic NOT explicitly installed (comes with fastapi)")

    # Python version
    if 'version = "3.11"' in body:
        ok("Python 3.11 target")
    else:
        warn("Python version != 3.11")


# ════════════════════════════════════════════════════════════
# 2. Root chaquopy plugin version
# ════════════════════════════════════════════════════════════
section("2. Root chaquopy plugin")

root_src = ROOT_GRADLE.read_text()
m = re.search(r'id\("com\.chaquo\.python"\)\s+version\s+"([^"]+)"\s+apply\s+false', root_src)
if not m:
    err("chaquopy plugin missing in root build.gradle.kts")
else:
    v = m.group(1)
    ok(f"chaquopy {v}")
    if v.startswith("16."):
        ok("chaquopy 16.x (supports Python 3.11)")
    elif v.startswith("15."):
        err(f"chaquopy {v} does not support Python 3.11 — need 16.x")
    else:
        warn(f"chaquopy {v} — verify Python 3.11 support")


# ════════════════════════════════════════════════════════════
# 3. App gradle — plugin + fileTree + abiFilters
# ════════════════════════════════════════════════════════════
section("3. App gradle — plugin + AAR + ABI")

# Plugin applied
if re.search(r'id\("com\.chaquo\.python"\)\s*$', src, re.MULTILINE):
    ok("chaquopy plugin applied in app")
else:
    err("chaquopy plugin NOT applied in app")

# fileTree for AAR
if "fileTree(mapOf" in src and "*.aar" in src:
    ok("fileTree includes *.aar from libs/")
else:
    err("fileTree for libs/*.aar missing")

# abiFilters inside ndk
dc = re.search(r'defaultConfig\s*\{([\s\S]*?)\n    \}', src)
if dc and "ndk {" in dc.group(1) and "abiFilters" in dc.group(1):
    ok("abiFilters inside ndk block")
else:
    warn("abiFilters not found inside ndk block")


# ════════════════════════════════════════════════════════════
# 4. Python backend imports — runtime deps
# ════════════════════════════════════════════════════════════
section("4. Python runtime imports (must match pip)")

py_root = REPO / "admin/android/app/src/main/python/backend"
if not py_root.exists():
    err("backend Python dir not found")
else:
    # Collect top-level imports from Python
    all_imports = set()
    for py in py_root.rglob("*.py"):
        txt = py.read_text()
        for m_ in re.finditer(r'^\s*(?:from|import)\s+([a-zA-Z_][\w]*)', txt, re.MULTILINE):
            all_imports.add(m_.group(1))

    # Known stdlib + pip packages
    stdlib = {
        "os", "sys", "json", "time", "datetime", "typing", "re", "uuid",
        "hashlib", "hmac", "base64", "secrets", "warnings", "pathlib",
        "contextlib", "sqlite3", "logging", "functools", "math", "socket",
        "shutil", "platform", "subprocess", "threading", "traceback",
        "asyncio", "importlib", "inspect", "collections", "io", "string",
        "binascii", "struct", "copy", "enum", "dataclasses", "abc",
    }
    pip_pkgs = {"fastapi", "pydantic", "jsonschema", "jwt", "uvicorn",
                "starlette", "anyio"}

    # What we actually import that's not stdlib
    external = all_imports - stdlib
    external = {i for i in external if not i.startswith("backend")}

    ok(f"External imports: {sorted(external)}")

    # Verify pip installs cover the imports
    installed = set(re.findall(r'install\("([^"]+)"\)', src))
    # Normalize (jwt comes from pyjwt, etc.)
    pkg_map = {
        "jwt": "pyjwt",
        "fastapi": "fastapi",
        "pydantic": None,  # comes with fastapi
        "jsonschema": "jsonschema",
        "starlette": "fastapi",  # transitive
        "anyio": "fastapi",
        "uvicorn": "uvicorn",
    }

    for imp in external:
        pip_name = pkg_map.get(imp, imp)
        if pip_name is None:
            ok(f"{imp} → transitive (via fastapi)")
        elif pip_name in installed:
            ok(f"{imp} ← {pip_name}")
        else:
            warn(f"import '{imp}' not explicitly covered by pip installs")


# ════════════════════════════════════════════════════════════
# 5. run_server.py syntax
# ════════════════════════════════════════════════════════════
section("5. run_server.py")

import ast
rs = REPO / "admin/android/app/src/main/python/run_server.py"
if not rs.exists():
    err("run_server.py missing")
else:
    try:
        ast.parse(rs.read_text())
        ok("run_server.py parses")
    except SyntaxError as e:
        err(f"Syntax error: {e}")

    txt = rs.read_text()
    for fn in ["def configure", "def start_backend", "def is_backend_ready",
               "def get_status", "def hello"]:
        if fn in txt:
            ok(f"{fn}()")
        else:
            err(f"missing: {fn}")


# ════════════════════════════════════════════════════════════
# 6. Kotlin — PythonServer + FamilyAdminApp
# ════════════════════════════════════════════════════════════
section("6. Kotlin bridge")

ps = REPO / "admin/android/app/src/main/java/com/admin/family/python/PythonServer.kt"
if ps.exists():
    src_kt = ps.read_text()
    for fn in ["fun init", "fun configure", "suspend fun startBackend",
               "suspend fun isBackendReady", "suspend fun status"]:
        if fn in src_kt:
            ok(f"PythonServer.{fn}()")
        else:
            err(f"missing: PythonServer.{fn}()")

app = REPO / "admin/android/app/src/main/java/com/admin/family/FamilyAdminApp.kt"
if app.exists():
    src_app = app.read_text()
    for call in ["PythonServer.init(this)", "PythonServer.configure(this)",
                 "PythonServer.startBackend()"]:
        if call in src_app:
            ok(f"FamilyAdminApp calls {call.split('(')[0]}")
        else:
            err(f"missing call: {call}")


# ════════════════════════════════════════════════════════════
# 7. tsnet-bridge Go files
# ════════════════════════════════════════════════════════════
section("7. tsnet-bridge Go")

go_dir = REPO / "admin/tsnet-bridge"
if go_dir.exists():
    for f in ["go.mod", "server.go", "log.go", "tools.go", "tunnel.go"]:
        if (go_dir / f).exists():
            ok(f"tsnet-bridge/{f}")
        else:
            err(f"missing: tsnet-bridge/{f}")

    # Check tsnet version
    gm = (go_dir / "go.mod").read_text()
    m = re.search(r"tailscale\.com v([\d.]+)", gm)
    if m and m.group(1).startswith("1.88"):
        ok(f"tailscale v{m.group(1)}")
    else:
        warn(f"tailscale version: {m.group(1) if m else 'unknown'}")

    # No obsolete API
    srv = (go_dir / "server.go").read_text()
    for bad in ["ts.Funnel(", "FunnelConfig"]:
        if bad in srv:
            err(f"obsolete Go API: {bad}")
    ok("no obsolete Funnel API")


# ════════════════════════════════════════════════════════════
# 8. Workflow
# ════════════════════════════════════════════════════════════
section("8. Workflow")

wf = REPO / ".github/workflows/admin-android.yml"
if wf.exists():
    wsrc = wf.read_text()
    for token in ["build-aar:", "build-admin:", "needs: build-aar",
                  "gomobile bind", "gradle :app:assembleDebug",
                  "download-artifact"]:
        if token in wsrc:
            ok(f"workflow: {token}")
        else:
            err(f"workflow missing: {token}")


# ════════════════════════════════════════════════════════════
# 9. Git status
# ════════════════════════════════════════════════════════════
section("9. Git status")

import subprocess
r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=REPO)
lines = [l for l in r.stdout.splitlines() if l.strip()]
ok(f"{len(lines)} files changed")

for line in lines:
    if "__pycache__" in line or ".pyc" in line:
        err(f"staged pycache: {line}")


# ════════════════════════════════════════════════════════════
# REPORT
# ════════════════════════════════════════════════════════════
print()
print("═" * 66)
print(f"  ✅ Passed   : {passed}")
print(f"  ⚠️  Warnings : {len(warnings)}")
print(f"  ❌ Errors   : {len(errors)}")
print("═" * 66)

if warnings:
    print("\n⚠️  WARNINGS:")
    for w in warnings:
        print(f"  • {w}")

if errors:
    print("\n❌ ERRORS:")
    for e in errors:
        print(f"  • {e}")
    print("\n🛑 NOT SAFE TO PUSH")
    sys.exit(1)

print("\n✅ ALL CHECKS PASSED — SAFE TO PUSH")
sys.exit(0)
