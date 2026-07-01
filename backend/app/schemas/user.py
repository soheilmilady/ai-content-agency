from datetime import datetime

from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8)
    role: Literal["admin", "editor", "writer"] = "writer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    role: Literal["admin", "editor", "writer"] | None = None
    is_active: bool | None = None


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8)
