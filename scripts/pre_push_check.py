#!/usr/bin/env python3
"""
Comprehensive pre-push verification for FamilySafety Phase 1.

Checks:
  1. File presence (all required files exist)
  2. Kotlin: braces, package, imports, no stale refs
  3. Go: brace balance, package, no obsolete API
  4. Python: syntax + import sanity
  5. Gradle: chaquopy + fileTree + ABI
  6. Workflow YAML: jobs + needs
  7. Cross-references between files
  8. Git status: no unexpected files
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path.cwd()
errors: list[str] = []
warnings: list[str] = []
passed = 0


def ok(msg: str) -> None:
    global passed
    passed += 1
    print(f"  ✅ {msg}")


def err(msg: str) -> None:
    errors.append(msg)
    print(f"  ❌ {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  ⚠️  {msg}")


def section(title: str) -> None:
    print()
    print("═" * 66)
    print(f"  {title}")
    print("═" * 66)


# ════════════════════════════════════════════════════════════
# 1. Required Files
# ════════════════════════════════════════════════════════════
section("1. Required Files")

REQUIRED = {
    # Go bridge
    "admin/tsnet-bridge/go.mod":                "go.mod",
    "admin/tsnet-bridge/tools.go":              "tools.go",
    "admin/tsnet-bridge/server.go":             "server.go",
    "admin/tsnet-bridge/log.go":                "log.go",
    "admin/tsnet-bridge/tunnel.go":             "tunnel.go",
    # Workflow
    ".github/workflows/admin-android.yml":      "workflow",
    ".github/workflows/contract-tests.yml":     "workflow",
    # Python
    "admin/android/app/src/main/python/run_server.py":          "python entry",
    "admin/android/app/src/main/python/backend/api/main.py":     "backend",
    # Kotlin (new)
    "admin/android/app/src/main/java/com/admin/family/FamilyAdminApp.kt": "app",
    "admin/android/app/src/main/java/com/admin/family/MainActivity.kt":   "activity",
    "admin/android/app/src/main/java/com/admin/family/python/PythonServer.kt": "kotlin py bridge",
    "admin/android/app/src/main/java/com/admin/family/tsnet/TsnetBridge.kt":   "tsnet bridge",
    "admin/android/app/src/main/java/com/admin/family/tsnet/TsnetProfile.kt":  "profile",
    # Gradle
    "admin/android/build.gradle.kts":           "root gradle",
    "admin/android/app/build.gradle.kts":       "app gradle",
    "admin/android/settings.gradle.kts":        "settings",
}

for rel, desc in REQUIRED.items():
    if (REPO / rel).exists():
        ok(f"{desc:20s} {rel}")
    else:
        err(f"MISSING ({desc}): {rel}")


# ════════════════════════════════════════════════════════════
# 2. Kotlin Files
# ════════════════════════════════════════════════════════════
section("2. Kotlin Files")

KT_ROOT = REPO / "admin/android/app/src/main/java/com/admin/family"
kt_files = sorted(KT_ROOT.rglob("*.kt"))
ok(f"{len(kt_files)} .kt files found")

# Package ↔ directory consistency
for kt in kt_files:
    src = kt.read_text()
    m = re.search(r"^package\s+([\w.]+)", src, re.MULTILINE)
    if not m:
        err(f"{kt.relative_to(REPO)}: missing package")
        continue
    expected_dir = m.group(1).replace(".", "/")
    if expected_dir not in str(kt.parent).replace("\\", "/"):
        err(f"{kt.relative_to(REPO)}: package '{m.group(1)}' mismatches dir")

# Brace balance
for kt in kt_files:
    src = kt.read_text()
    op, cl = src.count("{"), src.count("}")
    if op != cl:
        err(f"{kt.relative_to(REPO)}: braces unbalanced ({op}/{cl})")
if not any("braces unbalanced" in e for e in errors):
    ok("All Kotlin files have balanced braces")

# Stale tsnet references (except in tsnet package)
for kt in kt_files:
    if "tsnet" in str(kt).lower():
        continue
    src = kt.read_text()
    if "TsnetServerWrapper" in src or "tsnetbridge.Server" in src:
        err(f"{kt.relative_to(REPO)}: stale tsnet reference")

# ════════════════════════════════════════════════════════════
# 3. FamilyAdminApp.kt specific
# ════════════════════════════════════════════════════════════
section("3. FamilyAdminApp Integration")

app_kt = KT_ROOT / "FamilyAdminApp.kt"
if app_kt.exists():
    src = app_kt.read_text()

    # Required imports
    for imp in [
        "import com.admin.family.python.PythonServer",
        "import com.admin.family.tsnet.TsnetBridge",
        "import com.admin.family.tsnet.TsnetProfileStore",
    ]:
        if imp in src:
            ok(f"import: {imp.split('.')[-1]}")
        else:
            err(f"missing: {imp}")

    # Required DI fields
    for f in ["preferences", "settingsRepository", "apiClient", "deviceRepository",
              "tokenStore", "authRepository", "controlClient", "controlTokenStore",
              "tsnetBridge", "tsnetProfiles"]:
        if f"lateinit var {f}" in src:
            ok(f"field: {f}")
        else:
            err(f"missing field: {f}")

    # Required method calls
    for call in [
        "PythonServer.init(this)",
        "PythonServer.configure(this)",
        "PythonServer.startBackend()",
        "TsnetBridge(this)",
        "TsnetProfileStore(this)",
    ]:
        if call in src:
            ok(f"call: {call}")
        else:
            err(f"missing call: {call}")

# ════════════════════════════════════════════════════════════
# 4. PythonServer.kt
# ════════════════════════════════════════════════════════════
section("4. PythonServer.kt")

py_bridge = KT_ROOT / "python/PythonServer.kt"
if py_bridge.exists():
    src = py_bridge.read_text()

    for fn in ["fun init", "fun configure", "suspend fun startBackend",
               "suspend fun isBackendReady", "suspend fun status", "suspend fun hello"]:
        if fn in src:
            ok(f"{fn}()")
        else:
            err(f"missing: {fn}()")

    for imp in ["com.chaquo.python.Python", "com.chaquo.python.android.AndroidPlatform",
                "com.chaquo.python.PyObject"]:
        if imp in src:
            ok(f"import: {imp.split('.')[-1]}")
        else:
            err(f"missing import: {imp}")

# ════════════════════════════════════════════════════════════
# 5. TsnetBridge.kt / TsnetProfile.kt
# ════════════════════════════════════════════════════════════
section("5. Tsnet Kotlin Wrappers")

bridge_kt = KT_ROOT / "tsnet/TsnetBridge.kt"
if bridge_kt.exists():
    src = bridge_kt.read_text()
    for fn in ["suspend fun start", "suspend fun stop", "suspend fun listenAndProxy",
               "fun isRunning", "fun ip", "fun status", "fun stopAll"]:
        if fn in src:
            ok(f"TsnetBridge.{fn}()")
        else:
            err(f"missing: TsnetBridge.{fn}()")

    # gomobile call names — critical
    for call in ["Tsnetbridge.newServer", "srv.start()", "srv.iP4()",
                 "listenAndProxy(port.toLong(),"]:
        if call in src:
            ok(f"gomobile call: {call}")
        else:
            err(f"missing gomobile call: {call}")

profile_kt = KT_ROOT / "tsnet/TsnetProfile.kt"
if profile_kt.exists():
    src = profile_kt.read_text()
    for token in ["@Serializable", "data class TsnetProfile",
                  "class TsnetProfileStore", "fun list", "fun save",
                  "fun upsert", "fun remove"]:
        if token in src:
            ok(f"TsnetProfile: {token}")
        else:
            err(f"missing: {token}")

# ════════════════════════════════════════════════════════════
# 6. Go bridge
# ════════════════════════════════════════════════════════════
section("6. Go Bridge")

go_files = sorted((REPO / "admin/tsnet-bridge").glob("*.go"))
ok(f"{len(go_files)} .go files")

for gf in go_files:
    src = gf.read_text()
    op, cl = src.count("{"), src.count("}")
    if op != cl:
        err(f"{gf.name}: braces unbalanced ({op}/{cl})")
ok("Go braces balanced")

srv = REPO / "admin/tsnet-bridge/server.go"
if srv.exists():
    src = srv.read_text()
    # Required methods
    for fn in ["func (s *Server) Start", "func (s *Server) Stop",
               "func (s *Server) Status", "func (s *Server) IsRunning",
               "func (s *Server) IP4", "func (s *Server) LogFilePath",
               "func (s *Server) TailnetHostname", "func (s *Server) ProxyPort",
               "func (s *Server) ListenAndProxy", "func NewServer"]:
        if fn in src:
            ok(f"{fn}")
        else:
            err(f"missing: {fn}")

    # No obsolete API
    for bad in ["ts.Funnel(", "FunnelConfig", "status.Self.HostName"]:
        if bad in src:
            err(f"obsolete API: {bad}")
    ok("No obsolete Funnel API")

    # go.mod version
    gomod = REPO / "admin/tsnet-bridge/go.mod"
    gm = gomod.read_text()
    m = re.search(r"tailscale\.com v([\d.]+)", gm)
    if m:
        v = m.group(1)
        ok(f"tailscale.com {v}")
        if v.startswith("1.88"):
            ok("tailscale >= v1.88 (has netlink fix)")
        else:
            warn(f"tailscale {v} may lack Android netlink fix")

# ════════════════════════════════════════════════════════════
# 7. Python Assets
# ════════════════════════════════════════════════════════════
section("7. Python Assets")

py_assets = REPO / "admin/android/app/src/main/python"
py_files = list(py_assets.rglob("*.py"))
ok(f"{len(py_files)} .py files in assets")

# Syntax check
syn_errs = 0
for py in py_files:
    try:
        ast.parse(py.read_text(), filename=str(py))
    except SyntaxError as e:
        syn_errs += 1
        err(f"Syntax: {py.relative_to(py_assets)}: {e}")
if syn_errs == 0:
    ok("All Python assets parse cleanly")

# run_server.py entry points
rs = py_assets / "run_server.py"
if rs.exists():
    src = rs.read_text()
    for fn in ["def configure(", "def start_backend(", "def is_backend_ready(",
               "def get_status(", "def hello("]:
        if fn in src:
            ok(f"run_server: {fn}")
        else:
            err(f"missing: {fn}")

# ════════════════════════════════════════════════════════════
# 8. Gradle
# ════════════════════════════════════════════════════════════
section("8. Gradle Config")

root_g = REPO / "admin/android/build.gradle.kts"
app_g = REPO / "admin/android/app/build.gradle.kts"

if root_g.exists():
    src = root_g.read_text()
    m = re.search(r'id\("com\.chaquo\.python"\)\s+version\s+"([^"]+)"\s+apply\s+false', src)
    if m:
        v = m.group(1)
        ok(f"root: chaquopy {v}")
        if v.startswith("15."):
            err("chaquopy 15.x does not support Python 3.11 → need 16.x")
        elif v.startswith("16."):
            ok("chaquopy 16.x supports Python 3.11")

if app_g.exists():
    src = app_g.read_text()

    if "fileTree(mapOf" in src and "*.aar" in src:
        ok("app: fileTree includes *.aar from libs/")
    else:
        err("app: missing fileTree for libs/*.aar")

    if re.search(r'id\("com\.chaquo\.python"\)\s*$', src, re.MULTILINE):
        ok("app: chaquopy plugin applied")
    else:
        err("app: chaquopy plugin NOT applied")

    if re.search(r'chaquopy\s*\{', src):
        ok("app: chaquopy { } block present")

    m = re.search(r'version\s*=\s*"3\.11"', src)
    if m:
        ok("app: Python 3.11 targeted")

    if 'buildPython(' in src:
        ok("app: buildPython set")

    dc = re.search(r'defaultConfig\s*\{([\s\S]*?)\n\s{4}\}', src)
    if dc and "ndk {" in dc.group(1) and "abiFilters" in dc.group(1):
        ok("app: abiFilters inside ndk (defaultConfig)")
    else:
        warn("app: check abiFilters placement")

# ════════════════════════════════════════════════════════════
# 9. Workflow YAML
# ════════════════════════════════════════════════════════════
section("9. Workflow YAML")

wf = REPO / ".github/workflows/admin-android.yml"
if wf.exists():
    src = wf.read_text()

    if re.search(r"^  build-aar:", src, re.MULTILINE):
        ok("job: build-aar")
    else:
        err("missing job: build-aar")

    if re.search(r"^  build-admin:", src, re.MULTILINE):
        ok("job: build-admin")
    else:
        err("missing job: build-admin")

    if "needs: build-aar" in src:
        ok("build-admin depends on build-aar")
    else:
        err("build-admin does NOT depend on build-aar")

    if "download-artifact" in src and "tsnetbridge-aar" in src:
        ok("build-admin downloads AAR artifact")

    if "gomobile bind" in src:
        ok("build-aar runs gomobile bind")

    if "gradle :app:assembleDebug" in src:
        ok("build-admin runs assembleDebug")

# ════════════════════════════════════════════════════════════
# 10. Git status
# ════════════════════════════════════════════════════════════
section("10. Git Status")

try:
    r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=REPO)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    ok(f"{len(lines)} files changed")

    # Check for accidental large files
    for line in lines:
        # Files >5MB? check
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            path = parts[1].strip()
            if "..." in path:  # rename
                continue
            p = REPO / path
            if p.exists() and p.is_file():
                sz = p.stat().st_size
                if sz > 5_000_000:
                    warn(f"large file ({sz//1024//1024}MB): {path}")

    # No .aar tracked directly in APK
    for line in lines:
        if ".aar" in line and "libs" in line:
            warn(f"staged AAR (should come from artifact): {line}")

    # No __pycache__
    for line in lines:
        if "__pycache__" in line or ".pyc" in line:
            err(f"staged pycache: {line}")

except Exception as e:
    warn(f"git status failed: {e}")


# ════════════════════════════════════════════════════════════
# REPORT
# ════════════════════════════════════════════════════════════
print()
print("═" * 66)
print(f"  ✅ Passed  : {passed}")
print(f"  ⚠️  Warnings: {len(warnings)}")
print(f"  ❌ Errors  : {len(errors)}")
print("═" * 66)

if warnings:
    print("\n⚠️  WARNINGS:")
    for w in warnings:
        print(f"  • {w}")

if errors:
    print("\n❌ ERRORS:")
    for e in errors:
        print(f"  • {e}")
    print("\n🛑 NOT SAFE TO PUSH — fix errors first.")
    sys.exit(1)

print("\n✅ ALL CHECKS PASSED — SAFE TO PUSH")
sys.exit(0)
