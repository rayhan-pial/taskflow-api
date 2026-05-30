from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_workspace_member
from app.core.cursor import decode_cursor, encode_cursor
from app.core.exceptions import api_error
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.workspace_role import WorkspaceRole
from app.schemas.pagination import CursorPage, Page
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.services import workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    return await workspace_service.create_workspace(db, payload, owner_id=current_user.id)


@router.get("", response_model=Page[WorkspaceRead])
async def list_my_workspaces(
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    name: str | None = Query(default=None, max_length=255),
    sort: str | None = Query(
        default=None,
        description="Sort field. Prefix with '-' for descending. Allowed: name, created_at.",
    ),
    db: AsyncSession = Depends(get_db),
) -> Page[WorkspaceRead]:
    items, total = await workspace_service.list_workspaces_for_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        name=name,
        sort=sort,
    )
    return Page[WorkspaceRead](
        items=[WorkspaceRead.model_validate(w) for w in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/cursor", response_model=CursorPage[WorkspaceRead])
async def list_my_workspaces_cursor(
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[WorkspaceRead]:
    after_id: int | None = None
    if cursor is not None:
        data = decode_cursor(cursor)
        raw_id = data.get("id")
        if not isinstance(raw_id, int):
            raise api_error(
                status_code=400,
                code="invalid_cursor",
                message="Cursor is malformed.",
            )
        after_id = raw_id

    rows = await workspace_service.list_workspaces_for_user_cursor(
        db, user_id=current_user.id, limit=limit, after_id=after_id
    )

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = encode_cursor({"id": page_rows[-1].id}) if has_more else None

    return CursorPage[WorkspaceRead](
        items=[WorkspaceRead.model_validate(w) for w in page_rows],
        next_cursor=next_cursor,
        limit=limit,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.MEMBER))],
)
async def get_workspace(
    workspace_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    workspace = await workspace_service.get_workspace(db, workspace_id)
    if workspace is None:
        raise api_error(
            status_code=404,
            code="workspace_not_found",
            message="Workspace not found.",
        )
    return workspace


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.ADMIN))],
)
async def update_workspace(
    payload: WorkspaceUpdate,
    workspace_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    workspace = await workspace_service.update_workspace(db, workspace_id, payload)
    if workspace is None:
        raise api_error(
            status_code=404,
            code="workspace_not_found",
            message="Workspace not found.",
        )
    return workspace


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.OWNER))],
)
async def delete_workspace(
    workspace_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await workspace_service.delete_workspace(db, workspace_id)
    if not deleted:
        raise api_error(
            status_code=404,
            code="workspace_not_found",
            message="Workspace not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
