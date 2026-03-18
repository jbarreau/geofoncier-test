import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class UpdateRoleRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    permissions: list["PermissionInRoleResponse"]

    @field_validator("permissions", mode="before")
    @classmethod
    def extract_permissions(cls, v: object) -> object:
        # v is a list of RolePermission (junction) or Permission objects
        if v and hasattr(v[0], "permission"):
            return [rp.permission for rp in v]
        return v


class PermissionInRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
