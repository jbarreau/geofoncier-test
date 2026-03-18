import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from .roles import RoleResponse


class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime
    roles: list[RoleResponse]

    @field_validator("roles", mode="before")
    @classmethod
    def extract_roles(cls, v: object) -> object:
        # v is a list of UserRole (junction) or Role objects
        if v and hasattr(v[0], "role"):
            return [ur.role for ur in v]
        return v


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
