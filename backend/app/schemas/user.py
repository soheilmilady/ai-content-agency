import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("رمز عبور باید حداقل ۸ کاراکتر باشد.")
    if not re.search(r"\d", password):
        raise ValueError("رمز عبور باید حداقل شامل یک عدد باشد.")
    if not re.search(r"[a-zA-Z]", password):
        raise ValueError("رمز عبور باید حداقل شامل یک حرف انگلیسی باشد.")
    common_passwords = {"12345678", "password", "password123", "admin123", "123456789", "qwertyuiop"}
    if password.lower() in common_passwords:
        raise ValueError("این رمز عبور بسیار ساده و قابل حدس است. لطفاً رمز قوی‌تری انتخاب کنید.")
    return password


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8)
    role: Literal["admin", "editor", "writer"] = "writer"
    can_publish: bool = False

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    can_publish: bool
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    role: Literal["admin", "editor", "writer"] | None = None
    can_publish: bool | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_password_strength(v)
        return v


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_password_strength(v)
        return v
