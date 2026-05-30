from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import api_error
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.workspace_role import WorkspaceRole
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate

WORKSPACE_SORT_FIELDS = {
    "name": Workspace.name,
    "created_at": Workspace.created_at,
}


def _parse_sort(sort: str | None) -> tuple:
    if sort is None:
        return (Workspace.id.asc(),)
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    column = WORKSPACE_SORT_FIELDS.get(key)
    if column is None:
        raise api_error(
            status_code=400,
            code="invalid_sort",
            message=f"Cannot sort by '{key}'. Allowed: name, created_at.",
        )
    return (column.desc(),) if descending else (column.asc(),)


async def get_workspace(db: AsyncSession, workspace_id: int) -> Workspace | None:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    return result.scalar_one_or_none()


async def get_workspace_by_slug(db: AsyncSession, slug: str) -> Workspace | None:
    result = await db.execute(select(Workspace).where(Workspace.slug == slug))
    return result.scalar_one_or_none()


async def list_workspaces_for_user(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    name: str | None = None,
    sort: str | None = None,
) -> tuple[Sequence[Workspace], int]:
    base: Select = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
    )

    if name:
        base = base.where(Workspace.name.ilike(f"%{name}%"))

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = base.order_by(*_parse_sort(sort)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def list_workspaces_for_user_cursor(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
    after_id: int | None = None,
) -> Sequence[Workspace]:
    stmt: Select = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.id.asc())
        .limit(limit + 1)
    )
    if after_id is not None:
        stmt = stmt.where(Workspace.id > after_id)

    result = await db.execute(stmt)
    return result.scalars().all()


async def create_workspace(
    db: AsyncSession, payload: WorkspaceCreate, owner_id: int
) -> Workspace:
    if await get_workspace_by_slug(db, payload.slug) is not None:
        raise api_error(
            status_code=409,
            code="workspace_slug_taken",
            message="A workspace with this slug already exists.",
        )

    workspace = Workspace(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        owner_id=owner_id,
    )
    db.add(workspace)
    await db.flush()

    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
    )
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def update_workspace(
    db: AsyncSession, workspace_id: int, payload: WorkspaceUpdate
) -> Workspace | None:
    workspace = await get_workspace(db, workspace_id)
    if workspace is None:
        return None

    data = payload.model_dump(exclude_unset=True)

    if "slug" in data and data["slug"] != workspace.slug:
        if await get_workspace_by_slug(db, data["slug"]) is not None:
            raise api_error(
                status_code=409,
                code="workspace_slug_taken",
                message="A workspace with this slug already exists.",
            )
        workspace.slug = data["slug"]

    if "name" in data:
        workspace.name = data["name"]

    if "description" in data:
        workspace.description = data["description"]

    await db.commit()
    await db.refresh(workspace)
    return workspace


async def delete_workspace(db: AsyncSession, workspace_id: int) -> bool:
    workspace = await get_workspace(db, workspace_id)
    if workspace is None:
        return False
    await db.delete(workspace)
    await db.commit()
    return True


async def get_membership(
    db: AsyncSession, workspace_id: int, user_id: int
) -> WorkspaceMember | None:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
