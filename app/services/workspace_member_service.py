from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import api_error
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace_member import (
    WorkspaceMemberCreate,
    WorkspaceMemberUpdate,
)
from app.services.workspace_service import get_membership


async def list_members(
    db: AsyncSession, workspace_id: int, skip: int = 0, limit: int = 50
) -> Sequence[WorkspaceMember]:
    stmt = (
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def add_member(
    db: AsyncSession, workspace_id: int, payload: WorkspaceMemberCreate
) -> WorkspaceMember:
    user_exists = await db.execute(select(User.id).where(User.id == payload.user_id))
    if user_exists.scalar_one_or_none() is None:
        raise api_error(
            status_code=404,
            code="user_not_found",
            message="User does not exist.",
        )

    existing = await get_membership(db, workspace_id, payload.user_id)
    if existing is not None:
        raise api_error(
            status_code=409,
            code="member_already_exists",
            message="User is already a member of this workspace.",
        )

    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession,
    workspace_id: int,
    user_id: int,
    payload: WorkspaceMemberUpdate,
) -> WorkspaceMember | None:
    member = await get_membership(db, workspace_id, user_id)
    if member is None:
        return None

    member.role = payload.role
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(
    db: AsyncSession, workspace_id: int, user_id: int
) -> bool:
    member = await get_membership(db, workspace_id, user_id)
    if member is None:
        return False
    await db.delete(member)
    await db.commit()
    return True
