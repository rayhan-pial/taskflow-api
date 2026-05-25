from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import api_error
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.services import user_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        raw_payload = decode_token(token)
        payload = TokenPayload(**raw_payload)
    except (ValueError, ValidationError) as exc:
        raise api_error(
            status_code=401,
            code="invalid_token",
            message="Could not validate credentials.",
        ) from exc

    if payload.type != "access":
        raise api_error(
            status_code=401,
            code="wrong_token_type",
            message="Access token required.",
        )

    user = await user_service.get_user(db, int(payload.sub))
    if user is None:
        raise api_error(
            status_code=401,
            code="user_not_found",
            message="User no longer exists.",
        )
    if not user.is_active:
        raise api_error(
            status_code=401,
            code="inactive_user",
            message="User account is disabled.",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
