from __future__ import annotations

from pydantic import BaseModel, Field

from core_api.app.models.sql.user import UserRole


class RegisterRequest(BaseModel):
    tenant_slug: str = Field("default", min_length=1, max_length=128)
    tenant_name: str = Field("Default", min_length=1, max_length=256)
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=6, max_length=256)
    role: UserRole = Field(UserRole.EDITOR, description="User role: viewer=read-only, editor=read+write")


class LoginRequest(BaseModel):
    tenant_slug: str = Field("default", min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    tenant_id: str
    tenant_slug: str
    user_id: str
    email: str
    role: UserRole


