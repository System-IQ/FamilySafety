#!/usr/bin/env python3
"""
Exhaustive pre-flight check before pushing Chaquopy integration.
Validates: gradle files, Python assets, Kotlin bridge, cross-refs.
"""
import ast
import re
import sys
from pathlib import Path

REPO = Path.cwd()
errors: list[str] = []
warnings: list[str] = []
ok_count = 0


def ok(msg: str) -> None:
    global ok_count
    ok_count += 1
    print(f"  ✅ {msg}")


def err(msg: str) -> None:
    errors.append(msg)
    print(f"  ❌ {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  ⚠️  {msg}")


def section(title: str) -> None:
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {title}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ════════════════════════════════════════════════════════════
# 1. Gradle files
# ════════════════════════════════════════════════════════════
section("1. Gradle Configuration")

root_gradle = REPO / "admin/android/build.gradle.kts"
app_gradle = REPO / "admin/android/app/build.gradle.kts"

if not root_gradle.exists():
    err(f"Missing: {root_gradle.relative_to(REPO)}")
else:
    root_src = root_gradle.read_text()
    ok(f"root build.gradle.kts exists ({len(root_src)} chars)")

    # Chaquopy plugin declared with apply false
    m = re.search(r'id\("com\.chaquo\.python"\)\s+version\s+"([^"]+)"\s+apply\s+false', root_src)
    if m:
        ver = m.group(1)
        ok(f"chaquopy plugin declared: {ver}")
        # Chaquopy 15.x doesn't support Python 3.11
        if ver.startswith("15."):
            err(f"chaquopy {ver} does NOT support Python 3.11 — need 16.x")
        elif ver.startswith("16."):
            ok(f"chaquopy version {ver} supports Python 3.11")
        else:
            warn(f"chaquopy {ver} — verify supports Python 3.11")
    else:
        err("chaquopy plugin not declared in root build.gradle.kts")

if not app_gradle.exists():
    err(f"Missing: {app_gradle.relative_to(REPO)}")
else:
    app_src = app_gradle.read_text()
    ok(f"app build.gradle.kts exists ({len(app_src)} chars)")

    # Plugin applied (no version)
    if re.search(r'id\("com\.chaquo\.python"\)\s*$', app_src, re.MULTILINE):
        ok("chaquopy plugin applied in app")
    else:
        err("chaquopy plugin NOT applied in app/build.gradle.kts")

    # chaquopy { } block
    m = re.search(r'chaquopy\s*\{', app_src)
    if m:
        ok("chaquopy { } block present")
        # version = "3.11"
        m2 = re.search(r'version\s*=\s*"([\d.]+)"', app_src[m.start():m.start()+500])
        if m2:
            py_ver = m2.group(1)
            ok(f"Python version target: {py_ver}")
            if py_ver != "3.11":
                warn(f"Python {py_ver} — Chaquopy 16.1.0 supports 3.8-3.12")
        else:
            err("chaquopy version not set")
        # buildPython
        if 'buildPython(' in app_src:
            ok("buildPython() configured")
        else:
            err("buildPython() not configured")
    else:
        err("chaquopy { } block missing")

    # ABI filters — must be in ndk { } under defaultConfig
    ndk_block = re.search(r'ndk\s*\{([^}]*)\}', app_src)
    if ndk_block:
        if 'abiFilters' in ndk_block.group(1):
            ok("abiFilters in ndk block")
        else:
            warn("ndk block present but no abiFilters")
    else:
        warn("no ndk { } block found (Chaquopy may use defaults)")

    # lifecycle-service (needed later, but added now)
    if "lifecycle-service" in app_src:
        ok("androidx.lifecycle:lifecycle-service present")
    else:
        warn("lifecycle-service not in deps (will be needed in Phase 2)")


# ════════════════════════════════════════════════════════════
# 2. Python Assets
# ════════════════════════════════════════════════════════════
section("2. Python Assets")

py_root = REPO / "admin/android/app/src/main/python"

if not py_root.exists():
    err(f"Missing directory: {py_root.relative_to(REPO)}")
else:
    ok(f"Python assets dir exists: {py_root.relative_to(REPO)}")

    # run_server.py
    rs = py_root / "run_server.py"
    if rs.exists():
        ok("run_server.py present")
        rs_src = rs.read_text()
        for fn in ("def hello", "def start_backend", "def stop_backend"):
            if fn in rs_src:
                ok(f"  {fn}()")
            else:
                err(f"  missing: {fn}()")
    else:
        err("run_server.py MISSING")

    # backend/
    backend = py_root / "backend"
    if backend.exists():
        py_files = list(backend.rglob("*.py"))
        ok(f"backend/ contains {len(py_files)} .py files")
        # required modules
        for req in ("__init__.py", "api/main.py", "config.py", "db.py"):
            if (backend / req).exists():
                ok(f"  backend/{req}")
            else:
                err(f"  missing: backend/{req}")
    else:
        err("backend/ directory MISSING")

    # shared/contracts/
    contracts = py_root / "shared" / "contracts"
    if contracts.exists():
        json_files = list(contracts.rglob("*.json"))
        ok(f"shared/contracts/ contains {len(json_files)} .json schemas")
    else:
        err("shared/contracts/ MISSING")

    # Python syntax check — critical! Chaquopy will compile these
    print("\n  ── Python syntax check (all .py files) ──")
    syntax_errors = 0
    for py in py_root.rglob("*.py"):
        try:
            ast.parse(py.read_text(), filename=str(py))
        except SyntaxError as e:
            syntax_errors += 1
            err(f"Syntax error in {py.relative_to(py_root)}: {e}")
    if syntax_errors == 0:
        ok(f"All Python files parse cleanly (0 syntax errors)")
    else:
        err(f"{syntax_errors} files have syntax errors")


# ════════════════════════════════════════════════════════════
# 3. Kotlin Bridge
# ════════════════════════════════════════════════════════════
section("3. Kotlin Bridge")

bridge = REPO / "admin/android/app/src/main/java/com/admin/family/python/PythonServer.kt"

if not bridge.exists():
    err("PythonServer.kt MISSING")
else:
    ok("PythonServer.kt exists")
    src = bridge.read_text()

    # Required imports
    required_imports = [
        "import com.chaquo.python.PyObject",
        "import com.chaquo.python.Python",
        "import com.chaquo.python.android.AndroidPlatform",
        "import kotlinx.coroutines.Dispatchers",
        "import kotlinx.coroutines.withContext",
    ]
    for imp in required_imports:
        if imp in src:
            ok(f"  import: {imp.split('.')[-1]}")
        else:
            err(f"  missing import: {imp}")

    # Required functions
    required_fns = ["fun init", "suspend fun hello", "suspend fun startBackend",
                    "suspend fun stopBackend"]
    for fn in required_fns:
        if fn in src:
            ok(f"  {fn}()")
        else:
            err(f"  missing: {fn}()")

    # Python module name
    if '"run_server"' in src:
        ok("  module name: run_server")
    else:
        err("  module name mismatch (must be 'run_server')")

    # Brace balance
    if src.count("{") == src.count("}"):
        ok(f"  braces balanced ({src.count('{')})")
    else:
        err(f"  braces unbalanced: {{ {src.count('{')} }} {src.count('}')}")


# ════════════════════════════════════════════════════════════
# 4. FamilyAdminApp Integration
# ════════════════════════════════════════════════════════════
section("4. FamilyAdminApp Integration")

app_file = REPO / "admin/android/app/src/main/java/com/admin/family/FamilyAdminApp.kt"

if not app_file.exists():
    err("FamilyAdminApp.kt MISSING")
else:
    src = app_file.read_text()
    ok("FamilyAdminApp.kt exists")

    if "import com.admin.family.python.PythonServer" in src:
        ok("import PythonServer present")
    else:
        err("import PythonServer MISSING")

    if "PythonServer.init(this)" in src:
        ok("PythonServer.init(this) called in onCreate")
        # verify it's inside onCreate
        oncreate = re.search(r'override fun onCreate\(\)\s*\{([\s\S]*?)\n\s*\}', src)
        if oncreate and "PythonServer.init" in oncreate.group(1):
            ok("  init() is inside onCreate()")
        else:
            warn("  init() may be outside onCreate")
    else:
        err("PythonServer.init(this) NOT called")


# ════════════════════════════════════════════════════════════
# 5. Duplicate / Conflict Check
# ════════════════════════════════════════════════════════════
section("5. Conflict Detection")

# Root must NOT apply the plugin (only declare it)
if root_gradle.exists():
    root_src = root_gradle.read_text()
    if re.search(r'^\s+id\("com\.chaquo\.python"\)\s*$', root_src, re.MULTILINE):
        err("root has chaquopy plugin APPLIED (should be apply false only)")
    else:
        ok("root: chaquopy declared but not applied (correct)")

# App must apply plugin AND have block
if app_gradle.exists():
    app_src = app_gradle.read_text()
    if re.search(r'id\("com\.chaquo\.python"\)\s+version', app_src):
        err("app has chaquopy VERSION (should be without version)")
    else:
        ok("app: chaquopy plugin applied without version (correct)")

# No stale tsnet references
stale = []
for kt in (REPO / "admin/android/app/src/main/java").rglob("*.kt"):
    txt = kt.read_text()
    if "tsnetbridge" in txt or "TsnetServerWrapper" in txt:
        stale.append(kt.relative_to(REPO))
if stale:
    for s in stale:
        warn(f"stale tsnet reference: {s}")
else:
    ok("no stale tsnet references")


# ════════════════════════════════════════════════════════════
# 6. ABI / NDK Sanity
# ════════════════════════════════════════════════════════════
section("6. ABI / NDK")

if app_gradle.exists():
    app_src = app_gradle.read_text()
    # Common mistake: abiFilters outside ndk block
    dc = re.search(r'defaultConfig\s*\{([\s\S]*?)\n\s*\}', app_src)
    if dc:
        body = dc.group(1)
        if "ndk {" in body and "abiFilters" in body:
            ok("abiFilters inside defaultConfig.ndk (correct)")
        elif "abiFilters" in body and "ndk" not in body:
            err("abiFilters at defaultConfig level — must be inside ndk { }")
        else:
            warn("no abiFilters found — Chaquopy will build for all ABIs")


# ════════════════════════════════════════════════════════════
# Report
# ════════════════════════════════════════════════════════════
print()
print("=" * 64)
print(f"  ✅ Passed   : {ok_count}")
print(f"  ⚠️  Warnings : {len(warnings)}")
print(f"  ❌ Errors   : {len(errors)}")
print("=" * 64)

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

print("\n✅ SAFE TO PUSH")
sys.exit(0)
