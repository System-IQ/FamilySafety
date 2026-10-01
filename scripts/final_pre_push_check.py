#!/usr/bin/env python3
"""
FamilySafety — Final Pre-Push Verification.

Exhaustive check covering:
  1. Gradle config (plugins, versions, pins, ABI)
  2. Python assets (syntax, imports, compat layer)
  3. Kotlin cross-references (imports resolve, no stale classes)
  4. Go bridge completeness
  5. Workflow structure (jobs + needs + artifacts)
  6. Simulated Android runtime (pydantic v1 dry-run)
  7. Git working tree sanity
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path.cwd()
PKG = REPO / "admin/android/app/src/main/java/com/admin/family"
PY_ASSETS = REPO / "admin/android/app/src/main/python"
GO_DIR = REPO / "admin/tsnet-bridge"
WF = REPO / ".github/workflows/admin-android.yml"
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
    print("═" * 72)
    print(f"  {t}")
    print("═" * 72)


# ════════════════════════════════════════════════════════════
# 1. Gradle
# ════════════════════════════════════════════════════════════
section("1. Gradle configuration")

if not ROOT_GRADLE.exists():
    err("root build.gradle.kts missing")
else:
    src = ROOT_GRADLE.read_text()
    for plugin, ver in [
        ("com.android.application", "8.7.0"),
        ("org.jetbrains.kotlin.android", "2.0.21"),
        ("org.jetbrains.kotlin.plugin.compose", "2.0.21"),
        ("org.jetbrains.kotlin.plugin.serialization", "2.0.21"),
        ("com.chaquo.python", "16.1.0"),
    ]:
        pat = rf'id\("{re.escape(plugin)}"\)\s+version\s+"{re.escape(ver)}"\s+apply\s+false'
        if re.search(pat, src):
            ok(f"plugin: {plugin} {ver}")
        else:
            err(f"missing: {plugin} {ver} (apply false)")

if not APP_GRADLE.exists():
    err("app build.gradle.kts missing")
else:
    src = APP_GRADLE.read_text()

    # Plugin applied
    if re.search(r'id\("com\.chaquo\.python"\)\s*$', src, re.MULTILINE):
        ok("chaquopy plugin applied in app")
    else:
        err("chaquopy plugin NOT applied")

    # ABI
    dc = re.search(r'defaultConfig\s*\{([\s\S]*?)\n    \}', src)
    if dc and "ndk {" in dc.group(1) and "abiFilters" in dc.group(1):
        ok("abiFilters inside defaultConfig.ndk")
    else:
        err("abiFilters missing or misplaced")

    # Pip pins
    pins = re.findall(r'install\("([^"]+)"\)', src)
    expected = {
        "fastapi==0.99.1",
        "pydantic==1.10.15",
        "uvicorn==0.30.6",
        "pyjwt==2.8.0",
        "rfc3339-validator==0.1.4",
    }
    if set(pins) == expected:
        ok(f"pip pins: {sorted(pins)}")
    else:
        missing = expected - set(pins)
        extra = set(pins) - expected
        if missing:
            err(f"missing pins: {sorted(missing)}")
        if extra:
            warn(f"extra pins: {sorted(extra)}")

    # fileTree
    if "fileTree(mapOf" in src and "*.aar" in src:
        ok("fileTree for libs/*.aar present")
    else:
        err("fileTree for AAR missing")

    # biometry + fragment
    for dep in ["androidx.biometric:biometric", "androidx.fragment:fragment-ktx"]:
        if dep in src:
            ok(f"dep: {dep}")
        else:
            err(f"missing dep: {dep}")


# ════════════════════════════════════════════════════════════
# 2. Python assets
# ════════════════════════════════════════════════════════════
section("2. Python assets")

if not PY_ASSETS.exists():
    err("python assets dir missing")
else:
    py_files = list(PY_ASSETS.rglob("*.py"))
    ok(f"{len(py_files)} .py files")

    # Syntax check
    syntax_errs = 0
    for py in py_files:
        try:
            ast.parse(py.read_text(), filename=str(py))
        except SyntaxError as e:
            syntax_errs += 1
            err(f"Syntax: {py.relative_to(PY_ASSETS)}:{e.lineno}: {e.msg}")
    if syntax_errs == 0:
        ok("0 syntax errors")

    # _base_model
    bm = PY_ASSETS / "backend/_base_model.py"
    if bm.exists():
        ok("_base_model.py present")
        bm_src = bm.read_text()
        for token in ["PYDANTIC_V2", "class BaseModel", "def dump_json",
                      "def parse_obj", "def model_dump"]:
            if token in bm_src:
                ok(f"  {token}")
            else:
                err(f"  missing: {token}")
    else:
        err("_base_model.py MISSING")

    # Schema files use _BaseModel
    schema_files = sorted((PY_ASSETS / "backend").glob("schemas*.py"))
    ok(f"{len(schema_files)} schema files found")
    for sf in schema_files:
        if "_BaseModel" in sf.read_text():
            ok(f"  {sf.name}: uses _BaseModel")
        else:
            err(f"  {sf.name}: does NOT use _BaseModel")

    # No v2-only code outside _base_model
    v2_only_count = 0
    for py in (PY_ASSETS / "backend").rglob("*.py"):
        if py.name == "_base_model.py":
            continue
        src = py.read_text()
        for pat in [r'model_config\s*=', r'ConfigDict',
                    r'\.model_dump\(', r'\.model_validate\(']:
            for m in re.finditer(pat, src):
                line_start = src.rfind("\n", 0, m.start()) + 1
                line = src[line_start:src.find("\n", m.start())]
                if not line.strip().startswith("#"):
                    v2_only_count += 1
                    err(f"v2-only in {py.relative_to(PY_ASSETS)}: {line.strip()[:70]}")
    if v2_only_count == 0:
        ok("0 pydantic-v2-only references outside _base_model")

    # run_server.py
    rs = PY_ASSETS / "run_server.py"
    if rs.exists():
        rs_src = rs.read_text()
        for fn in ["def configure", "def start_backend", "def is_backend_ready",
                   "def get_status", "def hello"]:
            if fn in rs_src:
                ok(f"run_server: {fn}")
            else:
                err(f"run_server missing: {fn}")
    else:
        err("run_server.py MISSING")

    # contracts
    contracts = list((PY_ASSETS / "shared").rglob("*.json"))
    if len(contracts) >= 12:
        ok(f"{len(contracts)} contract schemas")
    else:
        warn(f"only {len(contracts)} contract schemas (expected 12+)")

    # Backend modules
    backend_files = list((PY_ASSETS / "backend").rglob("*.py"))
    if len(backend_files) >= 40:
        ok(f"{len(backend_files)} backend .py files")
    else:
        warn(f"only {len(backend_files)} backend .py files (expected 44)")


# ════════════════════════════════════════════════════════════
# 3. Kotlin
# ════════════════════════════════════════════════════════════
section("3. Kotlin files")

if not PKG.exists():
    err("Kotlin package dir missing")
else:
    kt_files = sorted(PKG.rglob("*.kt"))
    ok(f"{len(kt_files)} .kt files")

    # Deleted classes MUST NOT be referenced
    deleted = {
        "LoginScreen", "LoginState", "LoginViewModel",
        "AuthRepository", "AuthDto",
    }
    stale = []
    for kt in kt_files:
        src = kt.read_text()
        for d in deleted:
            # word boundary match, exclude comments
            for m in re.finditer(rf'\b{re.escape(d)}\b', src):
                line_start = src.rfind("\n", 0, m.start()) + 1
                line = src[line_start:src.find("\n", m.start())]
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                # TokenStore is a false positive (ControlTokenStore contains it)
                if d == "TokenStore":
                    # skip when preceded by "Control"
                    if "ControlTokenStore" in line:
                        continue
                stale.append(f"{kt.relative_to(PKG)}:{line.strip()[:70]}")
                break
    if not stale:
        ok("no stale references to deleted classes")
    else:
        for s in stale:
            err(f"stale ref: {s}")

    # Brace balance
    for kt in kt_files:
        src = kt.read_text()
        if src.count("{") != src.count("}"):
            err(f"{kt.relative_to(PKG)}: unbalanced braces")

    # Package path matches directory
    for kt in kt_files:
        src = kt.read_text()
        m = re.search(r'^package\s+([\w.]+)', src, re.MULTILINE)
        if m:
            expected = m.group(1).replace(".", "/")
            if expected not in str(kt.parent).replace("\\", "/"):
                err(f"{kt.relative_to(PKG)}: package/path mismatch")

    # AccessCode + Biometric wired
    key_files = {
        "data/auth/AccessCodeStore.kt": ["class AccessCodeStore", "var code", "var biometricEnabled"],
        "biometric/BiometricHelper.kt": ["class BiometricHelper", "suspend fun authenticate"],
        "ui/auth/AccessCodeScreen.kt": ["fun AccessCodeScreen"],
        "ui/auth/BiometricGateScreen.kt": ["fun BiometricGateScreen"],
        "ui/navigation/AppNavigation.kt": ["ACCESS_CODE", "BIOMETRIC_GATE", "CONTROL_ROOM"],
    }
    for rel, tokens in key_files.items():
        p = PKG / rel
        if not p.exists():
            err(f"missing: {rel}")
            continue
        src = p.read_text()
        missing = [t for t in tokens if t not in src]
        if missing:
            err(f"{rel}: missing {missing}")
        else:
            ok(f"{rel}: complete")

    # MainActivity extends FragmentActivity
    ma = (PKG / "MainActivity.kt").read_text()
    if "FragmentActivity" in ma:
        ok("MainActivity extends FragmentActivity")
    else:
        err("MainActivity does NOT extend FragmentActivity (BiometricPrompt needs it)")


# ════════════════════════════════════════════════════════════
# 4. Go bridge
# ════════════════════════════════════════════════════════════
section("4. Go bridge")

if not GO_DIR.exists():
    err("admin/tsnet-bridge missing")
else:
    for f in ["go.mod", "server.go", "log.go", "tools.go", "tunnel.go"]:
        p = GO_DIR / f
        if p.exists():
            ok(f"tsnet-bridge/{f}")
        else:
            err(f"missing: tsnet-bridge/{f}")

    gomod = (GO_DIR / "go.mod").read_text()
    m = re.search(r'tailscale\.com\s+v([\d.]+)', gomod)
    if m and m.group(1).startswith("1.88"):
        ok(f"tailscale v{m.group(1)}")
    else:
        warn(f"tailscale version: {m.group(1) if m else 'unknown'}")

    srv = (GO_DIR / "server.go").read_text()
    for fn in ["func NewServer", "func (s *Server) Start",
               "func (s *Server) Stop", "func (s *Server) IP4",
               "func (s *Server) ListenAndProxy"]:
        if fn in srv:
            ok(f"  {fn}")
        else:
            err(f"missing: {fn}")

    for bad in ["ts.Funnel(", "FunnelConfig"]:
        if bad in srv:
            err(f"obsolete API: {bad}")


# ════════════════════════════════════════════════════════════
# 5. Workflow
# ════════════════════════════════════════════════════════════
section("5. Workflow")

if not WF.exists():
    err(".github/workflows/admin-android.yml missing")
else:
    src = WF.read_text()
    for token in [
        "build-aar:", "build-admin:", "needs: build-aar",
        "gomobile bind", "assembleDebug", "download-artifact",
        "tsnetbridge-aar", "admin-debug-apk",
    ]:
        if token in src:
            ok(f"workflow: {token}")
        else:
            err(f"workflow missing: {token}")


# ════════════════════════════════════════════════════════════
# 6. Simulated Android runtime
# ════════════════════════════════════════════════════════════
section("6. Simulated Android runtime (pydantic v1 dry-run)")

import tempfile
_tmp = Path(tempfile.mkdtemp(prefix="fs_check_"))
import os
os.environ["FS_ENV"] = "production"
os.environ["FS_DB_PATH"] = str(_tmp / "check.db")
os.environ["FS_JWT_SECRET"] = "x" * 40
os.environ["FS_ACCESS_CODE"] = "test-access-code-12345678"

sys.path.insert(0, str(PY_ASSETS))
try:
    from backend._base_model import BaseModel, dump_json, parse_obj, model_dump
    import pydantic
    ok(f"_base_model imports (pydantic {pydantic.VERSION})")

    from backend.schemas import DeviceIn
    d = DeviceIn(
        device_id="dev_test", device_name="T", platform="android",
        android_version="14", app_version="1.0",
        management_state="managed", connection_state="online",
        battery={"level_percent": 78, "charging": False,
                 "timestamp": "2026-09-29T10:00:00Z"},
        last_seen="2026-09-29T10:00:00Z",
        location_capability={"supported": True,
                             "permission_state": "granted",
                             "background_supported": True},
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-29T10:00:00Z",
    )
    j = dump_json(d)
    assert "device_id" in j
    ok("DeviceIn constructs + dump_json returns dict")

    # Extra field rejected (extra='forbid')
    try:
        DeviceIn(
            device_id="dev_x", device_name="X", platform="android",
            android_version="14", app_version="1.0",
            management_state="managed", connection_state="online",
            battery={"level_percent": 50, "charging": False,
                     "timestamp": "2026-09-29T10:00:00Z"},
            last_seen="2026-09-29T10:00:00Z",
            location_capability={"supported": True,
                                 "permission_state": "granted",
                                 "background_supported": True},
            created_at="2026-09-01T00:00:00Z",
            updated_at="2026-09-29T10:00:00Z",
            extra_evil="x",
        )
        err("DeviceIn accepted extra field (should reject)")
    except Exception:
        ok("DeviceIn rejects extra fields")

    # Config access code
    from backend.config import settings
    assert settings.access_code == "test-access-code-12345678"
    ok("settings.access_code loaded from env")

    # Dependencies function exists
    from backend.auth.dependencies import get_current_user, _LOCAL_USER
    assert _LOCAL_USER["user_id"] == "local_admin"
    ok("dependencies: local_admin synthetic user present")

except Exception as exc:
    import traceback
    err(f"runtime import failed: {type(exc).__name__}: {exc}")
    traceback.print_exc()


# ════════════════════════════════════════════════════════════
# 7. Git status
# ════════════════════════════════════════════════════════════
section("7. Git status")

r = subprocess.run(["git", "status", "--short"], capture_output=True,
                   text=True, cwd=REPO)
lines = [l for l in r.stdout.splitlines() if l.strip()]
ok(f"{len(lines)} files changed")

for line in lines:
    if "__pycache__" in line or ".pyc" in line:
        err(f"staged pycache: {line}")
    if ".aar" in line and "libs" in line:
        warn(f"staged AAR (should come from CI artifact): {line}")


# ════════════════════════════════════════════════════════════
# REPORT
# ════════════════════════════════════════════════════════════
print()
print("═" * 72)
print(f"  ✅ Passed   : {passed}")
print(f"  ⚠️  Warnings : {len(warnings)}")
print(f"  ❌ Errors   : {len(errors)}")
print("═" * 72)

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
