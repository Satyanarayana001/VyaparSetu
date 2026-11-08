import os
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))   # lowered only in the test-suite

# A valid bcrypt hash of a random string: verified against when the user doesn't exist,
# so response time does not reveal which emails are registered.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds=_ROUNDS)).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_ROUNDS)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), (password_hash or _DUMMY_HASH).encode()) and password_hash is not None
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now,
               "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


class LoginThrottle:
    """Small in-memory brute-force guard (per email+client). Single-process only; see deployment notes."""

    def __init__(self):
        self._fails: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        cutoff = time.time() - settings.login_lockout_seconds
        self._fails[key] = [t for t in self._fails.get(key, []) if t > cutoff]
        return self._fails[key]

    def blocked(self, key: str) -> bool:
        return len(self._recent(key)) >= settings.login_max_failures

    def record_failure(self, key: str) -> None:
        self._recent(key).append(time.time())

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)


login_throttle = LoginThrottle()
