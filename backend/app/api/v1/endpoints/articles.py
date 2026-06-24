import base64
import json
from collections.abc import AsyncGenerator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db
from app.core.config import settings
from app.models.article import Article
from app.models.user import User
from app.schemas.article import (
    ArticleResponse,
    ArticleUpdate,
    GenerateRequest,
    PublishRequest,
)
from app.services.llm_gateway import LLMGateway
from app.services.seo_critic import SEOCritic
from app.services.seo_generator import SEOGenerator
from app.services.web_researcher import WebResearcher

router = APIRouter()


def _can_view_all_articles(user: User) -> bool:
    return user.role in ("admin", "editor")


def _can_view_article(user: User, article: Article) -> bool:
    if _can_view_all_articles(user):
        return True
    return article.author_id == user.id


def _assemble_content(outline: dict, sections_html: list[str]) -> str:
    parts = [f"<h1>{outline.get('h1', '')}</h1>"]
    for section, html in zip(outline.get("sections", []), sections_html):
        parts.append(f"<h2>{section.get('h2', '')}</h2>")
        parts.append(html)
    return "".join(parts)


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _audit_and_improve(
    critic: SEOCritic, content: str, keyword: str
) -> tuple[str, int]:
    audit_result = await critic.audit(content, keyword)
    score = int(audit_result.get("score", 0))
    improve_attempts = 0

    while score < 85 and improve_attempts < 2:
        content = await critic.improve(
            content, keyword, audit_result.get("issues", [])
        )
        audit_result = await critic.audit(content, keyword)
        score = int(audit_result.get("score", 0))
        improve_attempts += 1

    return content, score


async def _generate_article(
    topic: str,
    keyword: str,
    llm_model: str | None = None,
) -> tuple[dict, str, int]:
    # استفاده از مدل Groq به عنوان پیش‌فرض در صورت عدم ارسال از کلاینت
    target_model = llm_model or "groq/llama-3.3-70b-versatile"
    llm = LLMGateway(model=target_model)
    researcher = WebResearcher()
    generator = SEOGenerator(llm)
    critic = SEOCritic(llm)

    research_data = await researcher.research(topic)
    outline = await generator.generate_outline(topic, keyword, research_data)

    lsi_keywords = outline.get("lsi_keywords", [])
    sections = outline.get("sections", [])
    sections_html: list[str] = []

    accumulated_context = f"عنوان اصلی مقاله (H1): {outline.get('h1', keyword)}\n\n"

    for section in sections:
        h2_title = section.get("h2", "")
        content_angle = section.get("content_angle", "")
        h3_list = section.get("h3_list", [])
        key_points = section.get("key_points", [])

        html = await generator.draft_section(
            h2_title=h2_title,
            content_angle=content_angle,
            h3_list=h3_list,
            key_points=key_points,
            keyword=keyword,
            lsi_keywords=lsi_keywords,
            previous_context=accumulated_context,
        )
        sections_html.append(html)
        accumulated_context += f"\n=== بخش: {h2_title} ===\n{html}\n\n"

    full_content = _assemble_content(outline, sections_html)
    full_content, score = await _audit_and_improve(critic, full_content, keyword)

    return outline, full_content, score


@router.post("/articles/generate", response_model=ArticleResponse)
async def generate_article(
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    outline, content_html, score = await _generate_article(
        body.topic, body.keyword, body.llm_model
    )
    article = Article(
        title=outline.get("h1", body.keyword),
        content_html=content_html,
        meta_description=outline.get("meta_description", "")[:160],
        focus_keyword=body.keyword,
        seo_score=score,
        status="pending_approval",
        author_id=current_user.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def _build_stream_generator(
    db: Session,
    current_user: User,
    topic: str,
    keyword: str,
    llm_model: str | None,
):
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # بازگشتِ شکوهمندانهٔ چکِ کلید Groq
            if not getattr(settings, "GROQ_API_KEY", None):
                yield _sse_event(
                    {
                        "step": "error",
                        "message": "کلید GROQ_API_KEY در تنظیمات backend تنظیم نشده است.",
                    }
                )
                return

            target_model = llm_model or "groq/llama-3.3-70b-versatile"
            llm = LLMGateway(model=target_model)
            researcher = WebResearcher()
            generator = SEOGenerator(llm)
            critic = SEOCritic(llm)

            yield _sse_event({"step": "researching", "message": "در حال تحقیق زنده..."})
            research_data = await researcher.research(topic)

            yield _sse_event({"step": "outlining", "message": "در حال طراحی ساختار..."})
            outline = await generator.generate_outline(topic, keyword, research_data)

            lsi_keywords = outline.get("lsi_keywords", [])
            sections = outline.get("sections", [])
            total = len(sections)
            sections_html: list[str] = []

            accumulated_context = f"عنوان اصلی مقاله (H1): {outline.get('h1', keyword)}\n\n"

            for index, section in enumerate(sections, start=1):
                h2_title = section.get("h2", f"بخش {index}")
                yield _sse_event(
                    {
                        "step": "drafting",
                        "message": f"در حال نگارش بخش {index} از {total}: «{h2_title}»...",
                    }
                )

                html = await generator.draft_section(
                    h2_title=h2_title,
                    content_angle=section.get("content_angle", ""),
                    h3_list=section.get("h3_list", []),
                    key_points=section.get("key_points", []),
                    keyword=keyword,
                    lsi_keywords=lsi_keywords,
                    previous_context=accumulated_context,
                )
                sections_html.append(html)
                accumulated_context += f"\n=== بخش: {h2_title} ===\n{html}\n\n"

            full_content = _assemble_content(outline, sections_html)

            yield _sse_event({"step": "auditing", "message": "در حال بررسی سئو..."})
            full_content, score = await _audit_and_improve(critic, full_content, keyword)

            chunk_size = 20
            for i in range(0, len(full_content), chunk_size):
                yield _sse_event({"token": full_content[i : i + chunk_size]})

            article = Article(
                title=outline.get("h1", keyword),
                content_html=full_content,
                meta_description=outline.get("meta_description", "")[:160],
                focus_keyword=keyword,
                seo_score=score,
                status="pending_approval",
                author_id=current_user.id,
            )
            db.add(article)
            db.commit()
            db.refresh(article)

            yield _sse_event(
                {
                    "step": "done",
                    "article_id": article.id,
                    "seo_score": score,
                    "meta_description": article.meta_description,
                    "title": article.title,
                }
            )
        except Exception as exc:
            yield _sse_event(
                {
                    "step": "error",
                    "message": f"خطا در تولید محتوا: {exc}",
                }
            )

    return event_stream


@router.post("/articles/generate-stream")
async def generate_article_stream_post(
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return StreamingResponse(
        _build_stream_generator(
            db, current_user, body.topic, body.keyword, body.llm_model
        )(),
        media_type="text/event-stream",
    )


@router.get("/articles/generate-stream")
async def generate_article_stream(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    topic: str = Query(...),
    keyword: str = Query(...),
    llm_model: str | None = Query(None),
):
    return StreamingResponse(
        _build_stream_generator(db, current_user, topic, keyword, llm_model)(),
        media_type="text/event-stream",
    )


@router.get("/articles", response_model=list[ArticleResponse])
def list_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    query = db.query(Article)
    if not _can_view_all_articles(current_user):
        query = query.filter(Article.author_id == current_user.id)
    return query.order_by(Article.created_at.desc()).all()


@router.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    if not _can_view_article(current_user, article):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return article


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
def update_article(
    article_id: int,
    body: ArticleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    if not _can_view_article(current_user, article):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)

    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(
    article_id: int,
    body: PublishRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )
    if not _can_view_article(current_user, article):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    wp_url = body.wp_url or settings.WP_URL
    wp_username = body.wp_username or settings.WP_USERNAME
    wp_app_password = body.wp_app_password or settings.WP_APP_PASSWORD

    if not wp_url or not wp_username or not wp_app_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WordPress credentials are not configured",
        )

    credentials = base64.b64encode(
        f"{wp_username}:{wp_app_password}".encode()
    ).decode()

    post_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    payload = {
        "title": article.title,
        "content": article.content_html,
        "status": "publish",
        "meta": {"_yoast_wpseo_focuskw": article.focus_keyword},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                post_url,
                json=payload,
                headers={"Authorization": f"Basic {credentials}"},
            )
            response.raise_for_status()
            wp_data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WordPress publish failed: {exc}",
        ) from exc

    article.wp_post_id = wp_data.get("id")
    article.status = "published"
    db.commit()
    db.refresh(article)
    return article