from collections.abc import Sequence

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role, require_self_or_admin
from app.core.exceptions import api_error
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    return await user_service.create_user(db, payload)


@router.get(
    "",
    response_model=list[UserRead],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Sequence[User]:
    return await user_service.list_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int = Path(ge=1),
    _: User = Depends(require_self_or_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await user_service.get_user(db, user_id)
    if user is None:
        raise api_error(
            status_code=404, code="user_not_found", message="User not found."
        )
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    payload: UserUpdate,
    user_id: int = Path(ge=1),
    _: User = Depends(require_self_or_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await user_service.update_user(db, user_id, payload)
    if user is None:
        raise api_error(
            status_code=404, code="user_not_found", message="User not found."
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int = Path(ge=1),
    _: User = Depends(require_self_or_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await user_service.delete_user(db, user_id)
    if not deleted:
        raise api_error(
            status_code=404, code="user_not_found", message="User not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
