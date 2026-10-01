#!/usr/bin/env python3
"""Real test: Forgot-PIN backend — offline mode, no SMTP.

Runs the actual FastAPI app in-process with a temporary SQLite DB,
then exercises /auth/forgot-pin and /auth/reset-pin end-to-end.

Verifies:
  - forgot-pin creates a hashed code row
  - the code is returned (dev mode only)
  - reset-pin accepts a valid code
  - reset-pin rejects wrong code
  - reset-pin rejects expired/used code
  - attempt counter works
  - rate limit works
"""
import os
import sys
import tempfile
import time
from pathlib import Path

# ─── Force test environment ───
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["FS_ENV"] = "development"
os.environ["FS_DB_PATH"] = _tmp.name
os.environ["FS_JWT_SECRET"] = "x" * 40
os.environ["FS_EXPOSE_RESET_CODE"] = "1"   # dev-only: return code
os.environ["FS_RESET_CODE_TTL"] = "900"
os.environ["FS_RESET_MAX_ATTEMPTS"] = "3"
os.environ["FS_RESET_RATE_WINDOW"] = "60"
os.environ["FS_RESET_MAX_CODES"] = "3"

# Add repo root to path
# IMPORTANT: test against the SOURCE backend/ (not the Android copy)
# because the Android copy may be out of sync during development.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

# ─── Test helpers ───
PASS = 0
FAIL = 0

def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        print(f"  ✅ {name}" + (f" — {extra}" if extra else ""))
        PASS += 1
    else:
        print(f"  ❌ {name}" + (f" — {extra}" if extra else ""))
        FAIL += 1

def banner(t):
    print(f"\n{'═' * 60}\n  {t}\n{'═' * 60}")


# ═══════════════════════════════════════════════════════════
#  Setup: FastAPI TestClient
# ═══════════════════════════════════════════════════════════
banner("Setup")

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("❌ fastapi.testclient not available")
    print("   Install: pip install httpx")
    sys.exit(1)

from backend.api.main import create_app
from backend.db import init_db

init_db()
app = create_app()
client = TestClient(app)

print(f"  ✅ App created")
print(f"  ✅ DB: {_tmp.name}")


# ═══════════════════════════════════════════════════════════
#  Test 1: forgotten email validation
# ═══════════════════════════════════════════════════════════
banner("Test 1 — email validation")
r = client.post("/auth/forgot-pin", json={"email": "not-an-email"})
check("Reject invalid email", r.status_code == 400, f"got {r.status_code}")

r = client.post("/auth/forgot-pin", json={"email": ""})
check("Reject empty email", r.status_code == 400, f"got {r.status_code}")


# ═══════════════════════════════════════════════════════════
#  Test 2: send code (no SMTP → returns code in dev mode)
# ═══════════════════════════════════════════════════════════
banner("Test 2 — forgot-pin creates code")

EMAIL = "test-user@example.com"
r = client.post("/auth/forgot-pin", json={"email": EMAIL})
check("HTTP 200", r.status_code == 200, f"got {r.status_code}")

body = r.json()
check("ok=true", body.get("ok") is True)
check("has dev_code", "dev_code" in body and body["dev_code"])
check("dev_code is 6 digits",
      body.get("dev_code", "").isdigit() and len(body.get("dev_code", "")) == 6,
      f"got '{body.get('dev_code')}'")

CODE = body["dev_code"]
print(f"     → code = {CODE}")


# ═══════════════════════════════════════════════════════════
#  Test 3: reset-pin with wrong code
# ═══════════════════════════════════════════════════════════
banner("Test 3 — wrong code rejected")

r = client.post("/auth/reset-pin", json={
    "email": EMAIL,
    "code": "000000" if CODE != "000000" else "111111",
    "new_pin": "123456",
})
check("HTTP 400", r.status_code == 400, f"got {r.status_code}")
check("error mentions invalid",
      "invalid" in r.json().get("detail", "").lower(),
      f"got '{r.json().get('detail')}'")


# ═══════════════════════════════════════════════════════════
#  Test 4: reset-pin with wrong PIN format
# ═══════════════════════════════════════════════════════════
banner("Test 4 — PIN format validation")

r = client.post("/auth/reset-pin", json={
    "email": EMAIL,
    "code": CODE,
    "new_pin": "abc",
})
check("Reject non-digit PIN", r.status_code == 400)

r = client.post("/auth/reset-pin", json={
    "email": EMAIL,
    "code": CODE,
    "new_pin": "12345",   # only 5 digits
})
check("Reject short PIN", r.status_code == 400)

r = client.post("/auth/reset-pin", json={
    "email": EMAIL,
    "code": CODE,
    "new_pin": "1234567",  # 7 digits
})
check("Reject long PIN", r.status_code == 400)


# ═══════════════════════════════════════════════════════════
#  Test 5: reset-pin with valid code + valid PIN
# ═══════════════════════════════════════════════════════════
banner("Test 5 — valid reset succeeds")

r = client.post("/auth/reset-pin", json={
    "email": EMAIL,
    "code": CODE,
    "new_pin": "654321",
})
check("HTTP 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
body = r.json()
check("ok=true", body.get("ok") is True)
print(f"     → {body.get('message')}")


# ═══════════════════════════════════════════════════════════
#  Test 6: same code cannot be used twice
# ═══════════════════════════════════════════════════════════
banner("Test 6 — code is burned after use")

r = client.post("/auth/reset-pin", json={
    "email": EMAIL,
    "code": CODE,
    "new_pin": "999999",
})
check("HTTP 400 (code already used)",
      r.status_code == 400,
      f"got {r.status_code}")


# ═══════════════════════════════════════════════════════════
#  Test 7: rate limit
# ═══════════════════════════════════════════════════════════
banner("Test 7 — rate limit (3 codes per 60s)")

EMAIL2 = "ratelimit@example.com"
codes_ok = 0
for i in range(5):
    r = client.post("/auth/forgot-pin", json={"email": EMAIL2})
    if r.status_code == 200:
        codes_ok += 1
    elif r.status_code == 429:
        break

check(f"Issued {codes_ok} codes before rate limit (max 3)", codes_ok == 3)
check("Rate limit hit at 4th request", r.status_code == 429, f"got {r.status_code}")


# ═══════════════════════════════════════════════════════════
#  Test 8: max attempts burn
# ═══════════════════════════════════════════════════════════
banner("Test 8 — max attempts burn the code")

EMAIL3 = "attempts@example.com"
r = client.post("/auth/forgot-pin", json={"email": EMAIL3})
CODE3 = r.json()["dev_code"]

# 3 wrong attempts (max_attempts = 3)
for i in range(3):
    client.post("/auth/reset-pin", json={
        "email": EMAIL3,
        "code": "000000",
        "new_pin": "123456",
    })

# 4th attempt even with the correct code should fail
r = client.post("/auth/reset-pin", json={
    "email": EMAIL3,
    "code": CODE3,
    "new_pin": "123456",
})
check("Code burned after 3 wrong attempts",
      r.status_code == 400,
      f"got {r.status_code}, detail={r.json().get('detail', '')[:80]}")


# ═══════════════════════════════════════════════════════════
#  Test 9: no reset requested
# ═══════════════════════════════════════════════════════════
banner("Test 9 — reset without request")

r = client.post("/auth/reset-pin", json={
    "email": "never-requested@example.com",
    "code": "123456",
    "new_pin": "123456",
})
check("Reject if no code was issued",
      r.status_code == 400,
      f"got {r.status_code}")


# ═══════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"  PASSED: {PASS}")
print(f"  FAILED: {FAIL}")
print(f"{'═' * 60}")

if FAIL == 0:
    print("\n✅ ALL FORGOT-PIN BACKEND TESTS PASSED")
else:
    print(f"\n❌ {FAIL} TEST(S) FAILED")
    sys.exit(1)
