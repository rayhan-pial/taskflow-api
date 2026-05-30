from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_workspace_member
from app.core.exceptions import api_error
from app.db.session import get_db
from app.models.project import Project
from app.models.workspace_member import WorkspaceMember
from app.models.workspace_role import WorkspaceRole
from app.schemas.pagination import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project_service, workspace_service

workspace_projects_router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects",
    tags=["projects"],
)

projects_router = APIRouter(prefix="/projects", tags=["projects"])


def _require_project_access(
    min_role: WorkspaceRole = WorkspaceRole.MEMBER,
):
    async def checker(
        current_user: CurrentUser,
        project_id: Annotated[int, Path(ge=1)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> Project:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise api_error(
                status_code=404,
                code="project_not_found",
                message="Project not found.",
            )

        membership = await workspace_service.get_membership(
            db, project.workspace_id, current_user.id
        )
        if membership is None:
            raise api_error(
                status_code=403,
                code="not_a_member",
                message="You are not a member of this project's workspace.",
            )

        from app.api.deps import WORKSPACE_ROLE_RANK

        if WORKSPACE_ROLE_RANK[membership.role] < WORKSPACE_ROLE_RANK[min_role]:
            raise api_error(
                status_code=403,
                code="forbidden",
                message="You do not have permission to perform this action.",
            )

        return project

    return checker


@workspace_projects_router.get(
    "",
    response_model=Page[ProjectRead],
    dependencies=[Depends(require_workspace_member(WorkspaceRole.MEMBER))],
)
async def list_workspace_projects(
    workspace_id: int = Path(ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    name: str | None = Query(default=None, max_length=255),
    sort: str | None = Query(
        default=None,
        description="Sort field. Prefix with '-' for descending. Allowed: name, created_at.",
    ),
    db: AsyncSession = Depends(get_db),
) -> Page[ProjectRead]:
    items, total = await project_service.list_projects_for_workspace(
        db,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        name=name,
        sort=sort,
    )
    return Page[ProjectRead](
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@workspace_projects_router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_member(WorkspaceRole.ADMIN))],
)
async def create_workspace_project(
    payload: ProjectCreate,
    workspace_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
) -> Project:
    return await project_service.create_project(
        db, workspace_id=workspace_id, payload=payload
    )


@projects_router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project: Project = Depends(_require_project_access(WorkspaceRole.MEMBER)),
) -> Project:
    return project


@projects_router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(_require_project_access(WorkspaceRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Project:
    updated = await project_service.update_project(db, project.id, payload)
    if updated is None:
        raise api_error(
            status_code=404,
            code="project_not_found",
            message="Project not found.",
        )
    return updated


@projects_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project: Project = Depends(_require_project_access(WorkspaceRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await project_service.delete_project(db, project.id)
    if not deleted:
        raise api_error(
            status_code=404,
            code="project_not_found",
            message="Project not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
