from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Path
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import api_error
from app.core.security import decode_token
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.models.workspace_role import WorkspaceRole
from app.schemas.auth import TokenPayload
from app.services import user_service, workspace_service

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


def require_role(
    *allowed: Role,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    async def checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise api_error(
                status_code=403,
                code="forbidden",
                message="You do not have permission to perform this action.",
            )
        return current_user

    return checker


async def require_self_or_admin(
    current_user: CurrentUser,
    user_id: Annotated[int, Path(ge=1)],
) -> User:
    if current_user.id != user_id and current_user.role != Role.ADMIN:
        raise api_error(
            status_code=403,
            code="forbidden",
            message="You do not have permission to access this resource.",
        )
    return current_user


WORKSPACE_ROLE_RANK = {
    WorkspaceRole.MEMBER: 1,
    WorkspaceRole.ADMIN: 2,
    WorkspaceRole.OWNER: 3,
}


def require_workspace_member(
    min_role: WorkspaceRole = WorkspaceRole.MEMBER,
) -> Callable[..., Coroutine[Any, Any, WorkspaceMember]]:
    async def checker(
        current_user: CurrentUser,
        workspace_id: Annotated[int, Path(ge=1)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> WorkspaceMember:
        if await workspace_service.get_workspace(db, workspace_id) is None:
            raise api_error(
                status_code=404,
                code="workspace_not_found",
                message="Workspace not found.",
            )

        membership = await workspace_service.get_membership(
            db, workspace_id, current_user.id
        )
        if membership is None:
            raise api_error(
                status_code=403,
                code="not_a_member",
                message="You are not a member of this workspace.",
            )

        if WORKSPACE_ROLE_RANK[membership.role] < WORKSPACE_ROLE_RANK[min_role]:
            raise api_error(
                status_code=403,
                code="forbidden",
                message="You do not have permission to perform this action.",
            )

        return membership

    return checker
