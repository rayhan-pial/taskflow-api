import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkspaceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str) -> str:
        if not SLUG_PATTERN.match(value):
            raise ValueError(
                "Slug must be lowercase letters, digits, and hyphens (e.g. 'acme-engineering')."
            )
        return value


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not SLUG_PATTERN.match(value):
            raise ValueError(
                "Slug must be lowercase letters, digits, and hyphens (e.g. 'acme-engineering')."
            )
        return value


class WorkspaceRead(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
