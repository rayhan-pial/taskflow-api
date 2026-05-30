from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import api_error
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

PROJECT_SORT_FIELDS = {
    "name": Project.name,
    "created_at": Project.created_at,
}


def _parse_sort(sort: str | None) -> tuple:
    if sort is None:
        return (Project.id.asc(),)
    descending = sort.startswith("-")
    key = sort.lstrip("-")
    column = PROJECT_SORT_FIELDS.get(key)
    if column is None:
        raise api_error(
            status_code=400,
            code="invalid_sort",
            message=f"Cannot sort by '{key}'. Allowed: name, created_at.",
        )
    return (column.desc(),) if descending else (column.asc(),)


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def list_projects_for_workspace(
    db: AsyncSession,
    workspace_id: int,
    skip: int = 0,
    limit: int = 50,
    name: str | None = None,
    sort: str | None = None,
) -> tuple[Sequence[Project], int]:
    base: Select = select(Project).where(Project.workspace_id == workspace_id)

    if name:
        base = base.where(Project.name.ilike(f"%{name}%"))

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = base.order_by(*_parse_sort(sort)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def create_project(
    db: AsyncSession, workspace_id: int, payload: ProjectCreate
) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        workspace_id=workspace_id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession, project_id: int, payload: ProjectUpdate
) -> Project | None:
    project = await get_project(db, project_id)
    if project is None:
        return None

    data = payload.model_dump(exclude_unset=True)

    if "name" in data:
        project.name = data["name"]

    if "description" in data:
        project.description = data["description"]

    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: int) -> bool:
    project = await get_project(db, project_id)
    if project is None:
        return False
    await db.delete(project)
    await db.commit()
    return True
