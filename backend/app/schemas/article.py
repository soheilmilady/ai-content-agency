from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GenerateRequest(BaseModel):
    topic: str
    keyword: str
    llm_model: str | None = None


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content_html: str
    meta_description: str
    focus_keyword: str
    seo_score: int
    status: Literal["draft", "pending_approval", "approved", "published", "archived"]
    created_at: datetime


class ArticleListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    focus_keyword: str
    seo_score: int
    status: Literal["draft", "pending_approval", "approved", "published", "archived"]
    created_at: datetime


class PublishRequest(BaseModel):
    wp_url: str | None = None
    wp_username: str | None = None
    wp_app_password: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content_html: str | None = None
    meta_description: str | None = None
    status: Literal["draft", "pending_approval", "approved", "published", "archived"] | None = None
