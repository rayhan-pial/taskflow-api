import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str | int,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
) -> tuple[str, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": jti,
        "type": token_type,
    }
    encoded = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded, jti


def create_access_token(subject: str | int) -> str:
    settings = get_settings()
    token, _ = _create_token(
        subject,
        "access",
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    return token


def create_refresh_token(subject: str | int) -> tuple[str, str]:
    settings = get_settings()
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
