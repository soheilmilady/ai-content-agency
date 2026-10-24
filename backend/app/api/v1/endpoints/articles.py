import asyncio
import base64
import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.v1.deps import get_current_user, get_db
from app.core.config import settings
from app.core.limiter import limiter, get_dynamic_daily_limit
from app.core.network_security import is_safe_external_url
from app.models.article import Article
from app.models.user import User
from app.schemas.article import (
    ArticleResponse,
    ArticleListResponse,
    ArticleUpdate,
    GenerateRequest,
    PublishRequest,
    ArticleAssignRequest,
    ImproveRequest,
    ImprovePreviewResponse,
)
from app.services.llm_gateway import LLMGateway
from app.services.seo_generator import (
    SEOGenerator,
    fast_seo_scorer,
    sanitize_html
)
from app.services.article_orchestrator import ArticlePipeline, get_default_llm_model

logger = logging.getLogger(__name__)
router = APIRouter()

def _can_access(user: User, article: Article, read_only: bool = False) -> bool:
    if user.role == "admin":
        return True
    if read_only and user.role == "viewer":
        return True
    if article.author_id == user.id:
        return True
    if user.role == "editor":
        return any(editor.id == user.id for editor in article.assigned_editors)
    return False

def _can_publish(user: User) -> bool:
    return user.role == "admin" or user.can_publish





def _article_query_with_relations(db: Session):
    return db.query(Article).options(
        joinedload(Article.author),
        joinedload(Article.last_modified_by),
        selectinload(Article.assigned_editors),
    )


# ─────────────────────────────────────────────
# روت‌های API
# ─────────────────────────────────────────────

@router.post("/articles/generate-stream")
@limiter.limit(get_dynamic_daily_limit)
async def generate_stream_post(
    request: Request,
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    pipeline = ArticlePipeline(db, current_user, body.llm_model)
    return StreamingResponse(
        pipeline.execute_stream(body.topic, body.keyword, body.h2_keywords),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/articles/generate", response_model=ArticleResponse)
@limiter.limit(get_dynamic_daily_limit)
async def generate_no_stream(
    request: Request,
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        pipeline = ArticlePipeline(db, current_user, body.llm_model)
        return await pipeline.execute_no_stream(body.topic, body.keyword, body.h2_keywords)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/articles", response_model=list[ArticleListResponse])
def list_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0, description="تعداد رکوردهایی که نادیده گرفته می‌شوند"),
    limit: int = Query(50, ge=1, le=100, description="حداکثر تعداد رکوردهای خروجی"),
):
    query = _article_query_with_relations(db)
    if current_user.role not in ("admin", "viewer"):
        if current_user.role == "editor":
            query = query.filter(
                (Article.author_id == current_user.id) |
                (Article.assigned_editors.any(User.id == current_user.id))
            )
        else:
            query = query.filter(Article.author_id == current_user.id)
    return query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    article = _article_query_with_relations(db).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article, read_only=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")
    return article

@router.patch("/articles/{article_id}", response_model=ArticleResponse)
def update_article(article_id: int, body: ArticleUpdate, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    article = _article_query_with_relations(db).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    update_data = body.model_dump(exclude_unset=True)
    
    # 1. Mass Assignment Prevention: Status
    if "status" in update_data:
        if current_user.role not in ("admin", "editor"):
            if update_data["status"] not in ("draft", "pending_approval"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot publish this article directly.")

    # 2. XSS Prevention: Sanitize stored HTML
    if "content_html" in update_data and update_data["content_html"]:
        update_data["content_html"] = sanitize_html(update_data["content_html"])

    # 3. Reset status on writer edits to force review
    if current_user.role not in ("admin", "editor"):
        if "content_html" in update_data or "title" in update_data or "meta_description" in update_data:
            if article.status in ("approved", "published"):
                article.status = "pending_approval"

    for field, value in update_data.items():
        setattr(article, field, value)

    article.last_modified_by_id = current_user.id
    db.commit()
    db.refresh(article)
    return article

@router.post("/articles/{article_id}/assign", response_model=ArticleResponse)
def assign_editors(
    article_id: int, 
    body: ArticleAssignRequest, 
    db: Annotated[Session, Depends(get_db)], 
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can assign editors.")
    
    article = _article_query_with_relations(db).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
        
    editors = db.query(User).filter(User.id.in_(body.editor_ids)).all()
    article.assigned_editors = editors
    db.commit()
    db.refresh(article)
    return article

@router.post("/articles/{article_id}/improve-preview", response_model=ImprovePreviewResponse)
@limiter.limit(get_dynamic_daily_limit)
async def improve_article_preview(
    request: Request,
    article_id: int,
    body: ImproveRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    llm_model = body.llm_model or get_default_llm_model()
    llm = LLMGateway(model=llm_model)
    generator = SEOGenerator(llm)
    
    new_html = await generator.improve_article_html(article.content_html, body.instruction)
    new_score = fast_seo_scorer(new_html, article.focus_keyword)
    
    return ImprovePreviewResponse(
        new_html=new_html,
        new_seo_score=new_score,
        old_seo_score=article.seo_score
    )

@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    db.delete(article)
    db.commit()

@router.post("/articles/{article_id}/approve", response_model=ArticleResponse)
def approve_article(article_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.role not in ("admin", "editor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط ادمین و ویراستار می‌توانند مقاله را تایید کنند.")
        
    article = _article_query_with_relations(db).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
        
    article.status = "approved"
    db.commit()
    db.refresh(article)
    return article

@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(article_id: int, body: PublishRequest, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    if not _can_publish(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط admin و editor می‌توانند مقاله منتشر کنند.")

    article = _article_query_with_relations(db).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    if article.status not in ("approved", "published"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="فقط مقالاتی که تأیید شده‌اند (approved) قابل انتشار هستند.")

    system_wp_url = getattr(settings, "WP_URL", "")
    target_wp_url = body.wp_url or system_wp_url

    if not target_wp_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="آدرس سرور وردپرس تنظیم نشده است.")

    # SSRF Protection: validate destination URL
    is_safe, error_msg = is_safe_external_url(target_wp_url)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"آدرس وردپرس غیرمجاز است: {error_msg}")

    # Credential Isolation: Never send system default credentials to custom external targets
    if target_wp_url != system_wp_url:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط مدیر کل می‌تواند به وردپرس خارجی مقاله ارسال کند.")
        if not body.wp_username or not body.wp_app_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="برای سرور وردپرس سفارشی، نام کاربری و رمز عبور اختصاصی الزامی است.")
        wp_username = body.wp_username
        wp_password = body.wp_app_password
    else:
        wp_username = body.wp_username or getattr(settings, "WP_USERNAME", "")
        wp_password = body.wp_app_password or getattr(settings, "WP_APP_PASSWORD", "")

    if not wp_username or not wp_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اطلاعات وردپرس ناقص است.")

    wp_url = target_wp_url

    credentials = base64.b64encode(f"{wp_username}:{wp_password}".encode()).decode()

    wp_post_id = article.wp_post_id
    url_path = f"/wp-json/wp/v2/posts/{wp_post_id}" if wp_post_id else "/wp-json/wp/v2/posts"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{wp_url.rstrip('/')}{url_path}",
                json={
                    "title": article.title,
                    "content": article.content_html,
                    "status": "publish",
                    "meta": {
                        "_yoast_wpseo_focuskw": article.focus_keyword,
                        "_yoast_wpseo_metadesc": article.meta_description,
                    },
                },
                headers={"Authorization": f"Basic {credentials}"},
            )
            resp.raise_for_status()
            wp_data = resp.json()
    except Exception as exc:
        logger.error(f"WordPress publish error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="خطا در اتصال به وردپرس. به تیم فنی اطلاع داده شد.")

    article.wp_post_id = wp_data.get("id")
    article.status = "published"
    db.commit()
    db.refresh(article)
    return article