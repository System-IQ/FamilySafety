"""A1 Authentication — real hashing, real JWT, atomic rotation, real DB.

No mocks. No fakes. Every assertion hits a real HTTP route that
writes/reads a real SQLite DB and runs real scrypt + real HS256.
"""
import time

import pytest


# ============================================================
# REGISTER
# ============================================================

def test_register_creates_user(client):
    r = client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "a-very-long-password-1234",
        "display_name": "New Parent",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "new@example.com"
    assert body["display_name"] == "New Parent"
    assert body["user_id"].startswith("usr_")
    # Never leak password or hash
    assert "password" not in body
    assert "password_hash" not in body


def test_register_normalizes_email_case(client):
    r = client.post("/auth/register", json={
        "email": "MixedCase@Example.COM",
        "password": "long-enough-password-1",
        "display_name": "X",
    })
    assert r.status_code == 201
    assert r.json()["email"] == "mixedcase@example.com"


def test_register_duplicate_email_fails(client, registered_user):
    r = client.post("/auth/register", json={
        "email": registered_user["email"],
        "password": "another-long-password-1",
        "display_name": "Dup",
    })
    assert r.status_code == 409


def test_register_short_password_fails(client):
    r = client.post("/auth/register", json={
        "email": "short@example.com",
        "password": "12345",
        "display_name": "Short",
    })
    assert r.status_code == 422


def test_register_invalid_email_fails(client):
    r = client.post("/auth/register", json={
        "email": "not-an-email",
        "password": "long-enough-password-1",
        "display_name": "X",
    })
    assert r.status_code == 422


def test_register_extra_field_rejected(client):
    """Pydantic extra='forbid' — no privilege escalation via body."""
    r = client.post("/auth/register", json={
        "email": "extra@example.com",
        "password": "long-enough-password-1",
        "display_name": "X",
        "is_admin": True,
        "user_id": "usr_evil",
    })
    assert r.status_code == 422


# ============================================================
# LOGIN
# ============================================================

def test_login_valid_credentials(client, registered_user):
    r = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2   # JWT shape
    assert body["refresh_token"].count(".") == 2
    assert body["expires_in"] == 15 * 60


def test_login_wrong_password_fails(client, registered_user):
    r = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": "wrong-password-here",
    })
    assert r.status_code == 401


def test_login_unknown_email_fails(client):
    r = client.post("/auth/login", json={
        "email": "ghost@example.com",
        "password": "any-long-password-1234",
    })
    assert r.status_code == 401


def test_login_error_is_generic(client, registered_user):
    """Wrong password vs unknown email must return identical detail."""
    a = client.post("/auth/login", json={
        "email": registered_user["email"], "password": "wrong-password-here",
    })
    b = client.post("/auth/login", json={
        "email": "ghost@example.com", "password": "wrong-password-here",
    })
    assert a.status_code == 401 and b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"] == "invalid credentials"


# ============================================================
# PROTECTED (/me)
# ============================================================

def test_me_without_token_fails(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_invalid_token_fails(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_me_with_valid_token_succeeds(client, registered_user):
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    token = login.json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["user_id"] == registered_user["user"]["user_id"]


def test_me_with_expired_token_fails(client, registered_user):
    from backend.auth.tokens import create_access_token
    from backend.config import settings
    expired, _ = create_access_token(
        registered_user["user"]["user_id"],
        settings.jwt_secret,
        minutes=-1,
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_me_with_refresh_token_rejected(client, registered_user):
    """Refresh token must NOT work as an access token."""
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh = login.json()["refresh_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


# ============================================================
# REFRESH (rotation + replay protection)
# ============================================================

def test_refresh_rotates_tokens(client, registered_user):
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    old_refresh = login.json()["refresh_token"]

    r = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["refresh_token"] != old_refresh, "refresh must rotate"


def test_refresh_old_token_rejected_after_rotation(client, registered_user):
    """Replay protection: the old refresh token must be dead."""
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    old_refresh = login.json()["refresh_token"]

    ok = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert ok.status_code == 200

    replay = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401


def test_refresh_new_access_token_works(client, registered_user):
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh = login.json()["refresh_token"]

    refreshed = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200
    new_access = refreshed.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_refresh_with_garbage_fails(client):
    r = client.post("/auth/refresh", json={"refresh_token": "not-a-jwt-token-here"})
    assert r.status_code == 401


def test_refresh_revoked_fails(client, registered_user):
    """Manually revoked refresh must be rejected."""
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh = login.json()["refresh_token"]

    from backend.auth.tokens import decode_token
    from backend.auth import refresh_repo
    from backend.config import settings

    payload = decode_token(refresh, settings.jwt_secret, expected_type="refresh")
    refresh_repo.revoke_refresh_token(payload["jti"])

    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


def test_refresh_chain_works_multiple_times(client, registered_user):
    """Each refresh hands back a fresh pair that can be used again."""
    login = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    token = login.json()["refresh_token"]

    for i in range(3):
        r = client.post("/auth/refresh", json={"refresh_token": token})
        assert r.status_code == 200, f"iteration {i}: {r.text}"
        token = r.json()["refresh_token"]
