#!/usr/bin/env python3
"""Pre-flight check for Admin Android Kotlin files."""
import re, sys
from pathlib import Path

REPO = Path.cwd()
PKG = REPO / "admin/android/app/src/main/java/com/admin/family"

errors, warnings = [], []

def err(m): errors.append(m)
def warn(m): warnings.append(m)

if not PKG.exists():
    print(f"FATAL: {PKG} not found")
    sys.exit(2)

all_kt = sorted(PKG.rglob("*.kt"))
print(f"📁 Found {len(all_kt)} Kotlin files")

class FileInfo:
    def __init__(self, path):
        self.path = path
        self.rel = str(path.relative_to(REPO))
        self.content = path.read_text()

files = {str(f.relative_to(REPO)): FileInfo(f) for f in all_kt}

def get(suffix):
    """Exact match on the final path component, or ends-with on full path."""
    # prefer exact final-component match
    for rel, fi in files.items():
        if rel.endswith("/" + suffix) or rel == suffix:
            return fi
    # fallback: ends-with
    for rel, fi in files.items():
        if rel.endswith(suffix):
            return fi
    return None

# 1. Package vs path
for fi in files.values():
    m = re.search(r"^package\s+([\w.]+)", fi.content, re.M)
    if not m:
        err(f"{fi.rel}: missing package")
        continue
    expected = m.group(1).replace(".", "/")
    if expected not in fi.rel.replace("\\", "/"):
        err(f"{fi.rel}: package '{m.group(1)}' mismatches path")

# 2. Required files
required = [
    "FamilyAdminApp.kt", "MainActivity.kt",
    "data/api/ApiClient.kt", "data/api/dto/AuthDto.kt",
    "data/api/dto/DeviceDto.kt", "data/api/dto/HealthDto.kt",
    "data/api/dto/SystemMetricsDto.kt",
    "data/auth/TokenStore.kt", "data/prefs/AppPreferences.kt",
    "data/repository/AuthRepository.kt",
    "data/repository/DeviceRepository.kt",
    "data/repository/SettingsRepository.kt",
    "ui/auth/LoginScreen.kt", "ui/auth/LoginState.kt", "ui/auth/LoginViewModel.kt",
    "ui/controlroom/ControlRoomScreen.kt", "ui/controlroom/ControlRoomState.kt",
    "ui/controlroom/ControlRoomViewModel.kt",
    "ui/navigation/AppNavigation.kt",
    "ui/server/ServerDashboardScreen.kt", "ui/server/ServerDashboardState.kt",
    "ui/server/ServerDashboardViewModel.kt",
    "ui/settings/SettingsScreen.kt", "ui/settings/SettingsState.kt",
    "ui/settings/SettingsViewModel.kt",
]
for rel in required:
    if get(rel) is None:
        err(f"Missing: {rel}")

# 3. LoginViewModel ctor + factory
lvm = get("LoginViewModel.kt")
NEEDED = ["apiClient", "authRepo", "tokenStore", "settingsRepo", "preferences"]
if lvm:
    m = re.search(r"class\s+LoginViewModel\(\s*([\s\S]*?)\s*\)\s*:\s*ViewModel", lvm.content)
    if m:
        params = re.findall(r"private\s+val\s+(\w+)\s*:", m.group(1))
        for p in NEEDED:
            if p not in params:
                err(f"LoginViewModel ctor missing '{p}'")
    else:
        err("LoginViewModel ctor not parsed")

    m = re.search(r"class\s+LoginViewModelFactory\(\s*([\s\S]*?)\s*\)\s*:\s*ViewModelProvider\.Factory", lvm.content)
    if m:
        fparams = re.findall(r"private\s+val\s+(\w+)\s*:", m.group(1))
        for p in NEEDED:
            if p not in fparams:
                err(f"LoginViewModelFactory missing '{p}'")
    else:
        err("LoginViewModelFactory not parsed")

# 4. AppNavigation signature + factory call
nav = get("AppNavigation.kt")
NAV = ["deviceRepository", "settingsRepository", "apiClient",
       "authRepository", "tokenStore", "preferences"]
if nav:
    m = re.search(r"fun\s+AppNavigation\(([\s\S]*?)\)\s*\{", nav.content)
    if m:
        sig = re.findall(r"(\w+)\s*:", m.group(1))
        for p in NAV:
            if p not in sig:
                err(f"AppNavigation sig missing '{p}'")
    m = re.search(r"LoginViewModelFactory\s*\(([^)]*)\)", nav.content)
    if m:
        args = [a.strip() for a in m.group(1).split(",") if a.strip()]
        if len(args) != 5:
            err(f"LoginViewModelFactory called with {len(args)} args (expected 5): {args}")
    else:
        err("AppNavigation: no LoginViewModelFactory call")

# 5. MainActivity args
ma = get("MainActivity.kt")
if ma:
    for p in NAV:
        if f"{p} =" not in ma.content:
            err(f"MainActivity: missing '{p} = ...'")

# 6. FamilyAdminApp fields
app = get("FamilyAdminApp.kt")
if app:
    for f in ["preferences", "settingsRepository", "apiClient",
              "deviceRepository", "tokenStore", "authRepository"]:
        if f"lateinit var {f}" not in app.content:
            err(f"FamilyAdminApp: missing 'lateinit var {f}'")
        if f"{f} =" not in app.content:
            err(f"FamilyAdminApp: missing init '{f} = ...'")

# 7. ApiClient methods
ac = get("ApiClient.kt")
if ac:
    for m in ["fun health", "suspend fun login", "suspend fun register",
              "suspend fun me", "suspend fun listDevices",
              "suspend fun upsertDevice", "suspend fun systemMetrics",
              "fun setAuthToken", "fun getAuthToken", "fun updateBaseUrl",
              "val baseUrl", "authInterceptor"]:
        if m not in ac.content:
            err(f"ApiClient: missing '{m}'")

# 8. TokenStore
ts = get("TokenStore.kt")
if ts:
    for m in ["var accessToken", "var refreshToken", "var userEmail",
              "fun isLoggedIn", "fun clear"]:
        if m not in ts.content:
            err(f"TokenStore: missing '{m}'")

# 9. AppPreferences
ap = get("AppPreferences.kt")
if ap:
    for m in ["var apiBaseUrl", "var lastEmail", "fun normalize"]:
        if m not in ap.content:
            err(f"AppPreferences: missing '{m}'")
    if 'DEFAULT_BASE_URL = "http://127.0.0.1:8000/"' not in ap.content:
        warn("AppPreferences: DEFAULT_BASE_URL is not 127.0.0.1")

# 10. SettingsRepository
sr = get("SettingsRepository.kt")
if sr:
    for m in ["val apiBaseUrl", "fun saveBaseUrl", "fun resetToDefaults"]:
        if m not in sr.content:
            err(f"SettingsRepository: missing '{m}'")

# 11. AuthRepository
ar = get("AuthRepository.kt")
if ar:
    for m in ["suspend fun login", "fun logout", "fun isLoggedIn", "fun userEmail"]:
        if m not in ar.content:
            err(f"AuthRepository: missing '{m}'")

# 12. LoginScreen: BuildConfig import if used
ls = get("LoginScreen.kt")
if ls:
    if "BuildConfig" in ls.content and \
       "import com.admin.family.BuildConfig" not in ls.content:
        err("LoginScreen: uses BuildConfig, import missing")
    # Note: ContentType import removed intentionally — Compose 1.7.x
    # marks it internal; autofill works via KeyboardType + labels.

# 13. ControlRoom
cr = get("ControlRoomScreen.kt")
if cr and "onLogout" not in cr.content:
    err("ControlRoomScreen: missing 'onLogout'")
crs = get("ControlRoomState.kt")
if crs and "Unauthorized" not in crs.content:
    err("ControlRoomState: missing 'Unauthorized'")

# 14. No stale tsnet
for fi in files.values():
    for line in fi.content.splitlines():
        s = line.strip()
        if "tsnet" in s.lower() and not s.startswith("//") and not s.startswith("*"):
            err(f"{fi.rel}: stale tsnet: {s[:80]}")

# Report
print()
print("=" * 64)
print(f"  Files    : {len(all_kt)}")
print(f"  Errors   : {len(errors)}")
print(f"  Warnings : {len(warnings)}")
print("=" * 64)
if errors:
    print("\n❌ ERRORS:")
    for e in errors:
        print(f"  • {e}")
if warnings:
    print("\n⚠️  WARNINGS:")
    for w in warnings:
        print(f"  • {w}")
if not errors:
    print("\n✅ ALL CHECKS PASSED")
print()
sys.exit(1 if errors else 0)
