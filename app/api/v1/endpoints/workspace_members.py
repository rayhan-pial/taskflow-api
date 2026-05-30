from collections.abc import Sequence

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_member
from app.core.exceptions import api_error
from app.db.session import get_db
from app.models.workspace_member import WorkspaceMember
from app.models.workspace_role import WorkspaceRole
from app.schemas.workspace_member import (
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceMemberUpdate,
)
from app.services import workspace_member_service

router = APIRouter(
    prefix="/workspaces/{workspace_id}/members",
    tags=["workspace-members"],
)


@router.get(
    "",
    response_model=list[WorkspaceMemberRead],
    dependencies=[Depends(require_workspace_member(WorkspaceRole.MEMBER))],
)
async def list_workspace_members(
    workspace_id: int = Path(ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Sequence[WorkspaceMember]:
    return await workspace_member_service.list_members(
        db, workspace_id=workspace_id, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.ADMIN))],
)
async def add_workspace_member(
    payload: WorkspaceMemberCreate,
    workspace_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMember:
    return await workspace_member_service.add_member(
        db, workspace_id=workspace_id, payload=payload
    )


@router.patch(
    "/{user_id}",
    response_model=WorkspaceMemberRead,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.ADMIN))],
)
async def update_workspace_member(
    payload: WorkspaceMemberUpdate,
    workspace_id: int = Path(ge=1),
    user_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMember:
    member = await workspace_member_service.update_member_role(
        db, workspace_id=workspace_id, user_id=user_id, payload=payload
    )
    if member is None:
        raise api_error(
            status_code=404,
            code="member_not_found",
            message="User is not a member of this workspace.",
        )
    return member


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.ADMIN))],
)
async def remove_workspace_member(
    workspace_id: int = Path(ge=1),
    user_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await workspace_member_service.remove_member(
        db, workspace_id=workspace_id, user_id=user_id
    )
    if not deleted:
        raise api_error(
            status_code=404,
            code="member_not_found",
            message="User is not a member of this workspace.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
