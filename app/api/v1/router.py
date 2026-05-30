from fastapi import APIRouter

from app.api.v1.endpoints import auth, ping, projects, users, workspace_members, workspaces

api_router = APIRouter()
api_router.include_router(ping.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(workspace_members.router)
api_router.include_router(projects.workspace_projects_router)
api_router.include_router(projects.projects_router)
