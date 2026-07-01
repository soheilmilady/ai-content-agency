from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    topic: str
    keyword: str
    llm_model: str | None = None


class UserBasic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content_html: str
    meta_description: str
    focus_keyword: str
    seo_score: int
    status: Literal["draft", "pending_approval", "approved", "published", "archived"]
    author: UserBasic
    last_modified_by: UserBasic | None = None
    assigned_editors: list[UserBasic] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ArticleListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    focus_keyword: str
    seo_score: int
    status: Literal["draft", "pending_approval", "approved", "published", "archived"]
    author: UserBasic
    last_modified_by: UserBasic | None = None
    assigned_editors: list[UserBasic] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PublishRequest(BaseModel):
    wp_url: str | None = None
    wp_username: str | None = None
    wp_app_password: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content_html: str | None = None
    meta_description: str | None = None
    status: Literal["draft", "pending_approval", "approved", "published", "archived"] | None = None

class ArticleAssignRequest(BaseModel):
    editor_ids: list[int]

class ImproveRequest(BaseModel):
    instruction: str | None = None
    llm_model: str | None = None

class ImprovePreviewResponse(BaseModel):
    new_html: str
    new_seo_score: int
    old_seo_score: int
