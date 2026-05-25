from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import pwd_context, verify_password
from app.models.user import User
from app.services.user_service import get_user_by_email

_DUMMY_HASH = pwd_context.hash("dummy-password-for-timing")

_BLOCKLIST_PREFIX = "blocklist:"


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    user = await get_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def _blocklist_key(jti: str) -> str:
    return f"{_BLOCKLIST_PREFIX}{jti}"


async def blocklist_refresh_token(redis: Redis, jti: str, exp: int) -> None:
    ttl = exp - int(datetime.now(UTC).timestamp())
    if ttl <= 0:
        return
    await redis.set(_blocklist_key(jti), "1", ex=ttl)


async def is_refresh_token_blocklisted(redis: Redis, jti: str) -> bool:
    return await redis.exists(_blocklist_key(jti)) > 0
