"""Authentication endpoints — real hashing, JWT, rotation, AND audit."""
import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..audit_repo import record as audit_record
from ..auth import refresh_repo, users_repo
from ..auth.dependencies import get_current_user
from ..auth.passwords import hash_password, verify_password
from ..auth.tokens import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from ..config import settings
from ..observability import request_meta
from ..schemas_auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _issue_pair(user_id: str) -> TokenResponse:
    access, _ = create_access_token(
        user_id, settings.jwt_secret, settings.access_token_minutes
    )
    jti, refresh, expires_at = create_refresh_token(
        user_id, settings.jwt_secret, settings.refresh_token_days
    )
    refresh_repo.store_refresh_token(
        token_id=jti,
        user_id=user_id,
        token_hash=_sha256_hex(refresh),
        expires_at=expires_at,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_minutes * 60,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserPublic,
)
def register(body: RegisterRequest, request: Request) -> UserPublic:
    meta = request_meta(request)
    if users_repo.get_by_email(body.email) is not None:
        audit_record(
            action="user.register",
            resource_type="user",
            result="failure",
            reason="email already registered",
            **meta,
        )
        raise HTTPException(status_code=409, detail="email already registered")

    user_id = f"usr_{uuid.uuid4().hex[:16]}"
    pwd_hash = hash_password(body.password)
    user = users_repo.create_user(
        user_id=user_id,
        email=body.email,
        display_name=body.display_name,
        password_hash=pwd_hash,
    )
    audit_record(
        action="user.register",
        resource_type="user",
        result="success",
        actor_user_id=user["user_id"],
        resource_id=user["user_id"],
        **meta,
    )
    return UserPublic(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user["display_name"],
        created_at=user["created_at"],
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    meta = request_meta(request)
    user = users_repo.get_by_email(body.email)

    if user is None or not user["is_active"]:
        audit_record(
            action="user.login_failed",
            resource_type="user",
            result="failure",
            reason="invalid credentials",
            **meta,
        )
        raise HTTPException(status_code=401, detail="invalid credentials")

    if not verify_password(body.password, user["password_hash"]):
        audit_record(
            action="user.login_failed",
            resource_type="user",
            result="failure",
            actor_user_id=user["user_id"],
            reason="invalid credentials",
            **meta,
        )
        raise HTTPException(status_code=401, detail="invalid credentials")

    tokens = _issue_pair(user["user_id"])
    audit_record(
        action="user.login",
        resource_type="user",
        result="success",
        actor_user_id=user["user_id"],
        resource_id=user["user_id"],
        **meta,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, request: Request) -> TokenResponse:
    meta = request_meta(request)
    try:
        payload = decode_token(
            body.refresh_token, settings.jwt_secret, expected_type="refresh"
        )
    except TokenError as exc:
        audit_record(
            action="user.refresh_failed",
            resource_type="user",
            result="failure",
            reason=str(exc),
            **meta,
        )
        raise HTTPException(status_code=401, detail=str(exc))

    old_jti = payload.get("jti")
    user_id = payload.get("sub")
    if not old_jti or not user_id:
        audit_record(
            action="user.refresh_failed",
            resource_type="user",
            result="failure",
            actor_user_id=user_id,
            reason="malformed refresh",
            **meta,
        )
        raise HTTPException(status_code=401, detail="malformed refresh token")

    record = refresh_repo.get_refresh_token(old_jti)
    if record is None or record["revoked"]:
        audit_record(
            action="user.refresh_failed",
            resource_type="user",
            result="failure",
            actor_user_id=user_id,
            reason="revoked or unknown",
            **meta,
        )
        raise HTTPException(status_code=401, detail="refresh token revoked")
    if _sha256_hex(body.refresh_token) != record["token_hash"]:
        audit_record(
            action="user.refresh_failed",
            resource_type="user",
            result="failure",
            actor_user_id=user_id,
            reason="mismatch",
            **meta,
        )
        raise HTTPException(status_code=401, detail="refresh token mismatch")

    expires_at = datetime.strptime(
        record["expires_at"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        audit_record(
            action="user.refresh_failed",
            resource_type="user",
            result="failure",
            actor_user_id=user_id,
            reason="expired",
            **meta,
        )
        raise HTTPException(status_code=401, detail="refresh token expired")

    new_access, _ = create_access_token(
        user_id, settings.jwt_secret, settings.access_token_minutes
    )
    new_jti, new_refresh, new_expires_at = create_refresh_token(
        user_id, settings.jwt_secret, settings.refresh_token_days
    )

    ok = refresh_repo.consume_and_rotate(
        old_jti=old_jti,
        new_jti=new_jti,
        user_id=user_id,
        new_token_hash=_sha256_hex(new_refresh),
        new_expires_at=new_expires_at,
    )
    if not ok:
        audit_record(
            action="user.refresh_failed",
            resource_type="user",
            result="failure",
            actor_user_id=user_id,
            reason="already consumed",
            **meta,
        )
        raise HTTPException(status_code=401, detail="refresh token already consumed")

    audit_record(
        action="user.refresh",
        resource_type="user",
        result="success",
        actor_user_id=user_id,
        resource_id=user_id,
        **meta,
    )
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_minutes * 60,
    )


@router.get("/me", response_model=UserPublic)
def me(current: dict = Depends(get_current_user)) -> UserPublic:
    return UserPublic(
        user_id=current["user_id"],
        email=current["email"],
        display_name=current["display_name"],
        created_at=current["created_at"],
    )
