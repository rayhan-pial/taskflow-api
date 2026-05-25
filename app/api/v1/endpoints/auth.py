from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.exceptions import api_error
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RefreshRequest, Token, TokenPayload
from app.schemas.user import UserRead
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _decode_refresh(token: str) -> TokenPayload:
    try:
        payload = TokenPayload(**decode_token(token))
    except (ValueError, ValidationError) as exc:
        raise api_error(
            status_code=401,
            code="invalid_token",
            message="Invalid or expired token.",
        ) from exc

    if payload.type != "refresh":
        raise api_error(
            status_code=401,
            code="wrong_token_type",
            message="Refresh token required.",
        )
    return payload


def _issue_tokens(user_id: int) -> Token:
    access = create_access_token(user_id)
    refresh, _ = create_refresh_token(user_id)
    return Token(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await auth_service.authenticate_user(
        db, form_data.username, form_data.password
    )
    if user is None:
        raise api_error(
            status_code=401,
            code="invalid_credentials",
            message="Incorrect email or password.",
        )
    return _issue_tokens(user.id)


@router.post("/refresh", response_model=Token)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Token:
    payload = _decode_refresh(body.refresh_token)

    if await auth_service.is_refresh_token_blocklisted(redis, payload.jti):
        raise api_error(
            status_code=401,
            code="token_revoked",
            message="Refresh token has been revoked.",
        )

    user = await user_service.get_user(db, int(payload.sub))
    if user is None or not user.is_active:
        raise api_error(
            status_code=401,
            code="user_not_found",
            message="User no longer exists.",
        )

    await auth_service.blocklist_refresh_token(redis, payload.jti, payload.exp)
    return _issue_tokens(user.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    redis: Redis = Depends(get_redis),
) -> Response:
    payload = _decode_refresh(body.refresh_token)
    await auth_service.blocklist_refresh_token(redis, payload.jti, payload.exp)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> User:
    return current_user
