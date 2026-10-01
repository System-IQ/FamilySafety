"""Password hashing using stdlib scrypt.

No external deps. No Rust. Pure stdlib.
Format: scrypt$N$r$p$salt_b64$hash_b64  (self-describing, future-proof)
"""
import base64
import hashlib
import hmac
import os

_N = 2 ** 14
_R = 8
_P = 1
_DKLEN = 32
_SALT_LEN = 16

MIN_PASSWORD_LEN = 12
MAX_PASSWORD_LEN = 128


def hash_password(password: str) -> str:
    """Return 'scrypt$N$r$p$salt_b64$hash_b64'."""
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    if not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
        raise ValueError(
            f"password length must be {MIN_PASSWORD_LEN}..{MAX_PASSWORD_LEN}"
        )
    salt = os.urandom(_SALT_LEN)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N, r=_R, p=_P,
        dklen=_DKLEN,
    )
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verify. Never raises. Always returns bool."""
    try:
        if not isinstance(password, str) or not isinstance(stored, str):
            return False
        parts = stored.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        if n <= 0 or r <= 0 or p <= 0:
            return False
        salt = base64.b64decode(parts[4])
        expected = base64.b64decode(parts[5])
        if len(expected) == 0:
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n, r=r, p=p,
            dklen=len(expected),
        )
        return hmac.compare_digest(derived, expected)
    except Exception:
        return False
