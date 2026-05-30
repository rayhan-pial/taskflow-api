from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.workspace_role import WorkspaceRole


class WorkspaceMemberCreate(BaseModel):
    user_id: int
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int
    role: WorkspaceRole
    created_at: datetime
    updated_at: datetime
