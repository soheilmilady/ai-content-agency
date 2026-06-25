"""
articles.py v2 — Grounded Generation + Real Streaming
تغییرات نسبت به نسخه قبل:
- استفاده از distribute_facts_to_sections برای کاهش hallucination
- streaming واقعی: هر بخش به محض آماده شدن به فرانت می‌رسه
- تاخیر هوشمند قابل تنظیم از env
- چک API key برای هر دو Groq و OpenRouter
- پیام‌های خطای فارسی واضح
"""
import asyncio
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
from app.services.seo_generator import (
    SEOGenerator,
    distribute_facts_to_sections,
    extract_written_titles,
)
from app.services.web_researcher import WebResearcher

router = APIRouter()

# تاخیر بین بخش‌ها — قابل تنظیم از Render Environment Variables
_SECTION_DELAY: float = float(getattr(settings, "SECTION_DELAY_SECONDS", "3.0"))


# ─────────────────────────────────────────────
# توابع کمکی
# ─────────────────────────────────────────────

def _can_view_all(user: User) -> bool:
    return user.role in ("admin", "editor")


def _can_access(user: User, article: Article) -> bool:
    return _can_view_all(user) or article.author_id == user.id


def _can_publish(user: User) -> bool:
    return user.role in ("admin", "editor")


def _has_api_key() -> bool:
    """حداقل یک API key تنظیم شده باشد."""
    return bool(
        getattr(settings, "GROQ_API_KEY", None)
        or getattr(settings, "OPENROUTER_API_KEY", None)
    )


def _default_model() -> str:
    """مدل پیش‌فرض بر اساس API key موجود."""
    if getattr(settings, "GROQ_API_KEY", None):
        return "groq/llama-3.3-70b-versatile"
    return getattr(settings, "DEFAULT_LLM_MODEL", "openai/gpt-4o-mini")


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _assemble_html(outline: dict, sections_html: list[str]) -> str:
    """HTML نهایی مقاله را از outline و بخش‌های نوشته‌شده می‌سازد."""
    parts = [f"<h1>{outline.get('h1', '')}</h1>"]
    for section, html in zip(outline.get("sections", []), sections_html):
        h2 = section.get("h2", "")
        if h2:
            parts.append(f"<h2>{h2}</h2>")
        if html:
            parts.append(html)
    return "".join(parts)


def _extract_facts(research_data: dict) -> list[str]:
    """facts را از خروجی web researcher استخراج می‌کند."""
    snippets = research_data.get("snippets", [])
    if isinstance(snippets, list) and snippets:
        return [s for s in snippets if isinstance(s, str) and len(s) > 20]

    content = research_data.get("content", "")
    if isinstance(content, str) and content:
        # تقسیم به جملات کوتاه
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20]
        return sentences[:15]

    return []


async def _run_seo_audit(
    critic: SEOCritic, content: str, keyword: str
) -> tuple[str, int]:
    """ممیزی SEO و بهبود خودکار تا ۲ بار."""
    audit = await critic.audit(content, keyword)
    score = int(audit.get("score", 0))

    for _ in range(2):
        if score >= 85:
            break
        content = await critic.improve(content, keyword, audit.get("issues", []))
        audit = await critic.audit(content, keyword)
        score = int(audit.get("score", 0))

    return content, score


def _save_article(
    db: Session,
    outline: dict,
    content_html: str,
    keyword: str,
    score: int,
    author_id: int,
) -> Article:
    """مقاله را در دیتابیس ذخیره می‌کند."""
    article = Article(
        title=outline.get("h1", keyword),
        content_html=content_html,
        meta_description=outline.get("meta_description", "")[:160],
        focus_keyword=keyword,
        seo_score=score,
        status="pending_approval",
        author_id=author_id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


# ─────────────────────────────────────────────
# موتور اصلی تولید محتوا
# ─────────────────────────────────────────────

def _build_stream(
    db: Session,
    current_user: User,
    topic: str,
    keyword: str,
    llm_model: str | None,
):
    """
    generator اصلی streaming.
    هر بخش به محض آماده شدن با رویداد section_ready ارسال می‌شود.
    """
    async def stream() -> AsyncGenerator[str, None]:
        try:
            if not _has_api_key():
                yield _sse({
                    "step": "error",
                    "message": "API key تنظیم نشده. GROQ_API_KEY یا OPENROUTER_API_KEY را در Render تنظیم کنید.",
                })
                return

            model = llm_model or _default_model()
            llm = LLMGateway(model=model)
            generator = SEOGenerator(llm)
            critic = SEOCritic(llm)
            researcher = WebResearcher()

            # ── مرحله ۱: تحقیق زنده ──────────────────────────
            yield _sse({"step": "researching", "message": "در حال جستجو و تحقیق..."})
            research_data = await researcher.research(topic)
            all_facts = _extract_facts(research_data)

            # ── مرحله ۲: طراحی ساختار ────────────────────────
            yield _sse({"step": "outlining", "message": "در حال طراحی ساختار مقاله..."})
            outline = await generator.generate_outline(topic, keyword, research_data)

            sections = outline.get("sections", [])
            lsi_keywords = outline.get("lsi_keywords", [])
            domain_glossary = outline.get("domain_glossary", {})
            total = len(sections)

            # توزیع facts به بخش‌های مرتبط
            facts_map = distribute_facts_to_sections(sections, all_facts)

            sections_html: list[str] = []
            # فقط عناوین H1 در context اولیه — نه HTML کامل
            accumulated_titles = f"عنوان اصلی: {outline.get('h1', keyword)}"

            # ── مرحله ۳: نگارش بخش به بخش ───────────────────
            for idx, section in enumerate(sections, start=1):
                h2 = section.get("h2", f"بخش {idx}")

                yield _sse({
                    "step": "drafting",
                    "message": f"نگارش بخش {idx} از {total}: «{h2}»",
                    "progress": round((idx - 1) / total * 100),
                })

                # تاخیر هوشمند فقط بین بخش‌ها
                if idx > 1 and _SECTION_DELAY > 0:
                    await asyncio.sleep(_SECTION_DELAY)

                core_thesis = (
                    section.get("core_thesis")
                    or section.get("content_angle")
                    or f"توضیح و بررسی {h2}"
                )
                section_facts = facts_map.get(h2, [])

                html = await generator.draft_section(
                    h2_title=h2,
                    core_thesis=core_thesis,
                    h3_list=section.get("h3_list", []),
                    keyword=keyword,
                    lsi_keywords=lsi_keywords,
                    domain_glossary=domain_glossary,
                    section_facts=section_facts,
                    written_titles=accumulated_titles,
                    required_facts=section.get("required_facts", []),
                )

                sections_html.append(html)
                # فقط عنوان جدید اضافه می‌شود — نه HTML کامل
                accumulated_titles += f" | {h2}"

                # ارسال فوری بخش به فرانت
                yield _sse({
                    "step": "section_ready",
                    "index": idx,
                    "total": total,
                    "h2": h2,
                    "html": html,
                    "facts_used": len(section_facts),
                })

            # ── مرحله ۴: ممیزی SEO ───────────────────────────
            yield _sse({"step": "auditing", "message": "در حال ممیزی و بهینه‌سازی سئو..."})
            full_content = _assemble_html(outline, sections_html)
            full_content, score = await _run_seo_audit(critic, full_content, keyword)

            # ── مرحله ۵: ارسال محتوای نهایی token به token ──
            # فرانت از "token" برای نمایش در editor استفاده می‌کند
            chunk_size = 50
            for i in range(0, len(full_content), chunk_size):
                yield _sse({"token": full_content[i: i + chunk_size]})

            # ── مرحله ۶: ذخیره در دیتابیس ────────────────────
            article = _save_article(db, outline, full_content, keyword, score, current_user.id)

            yield _sse({
                "step": "done",
                "article_id": article.id,
                "seo_score": score,
                "title": article.title,
                "meta_description": article.meta_description,
                "facts_total": len(all_facts),
            })

        except asyncio.TimeoutError:
            yield _sse({
                "step": "error",
                "message": "زمان پاسخ مدل تمام شد. لطفاً دوباره تلاش کنید.",
            })
        except Exception as exc:
            yield _sse({
                "step": "error",
                "message": f"خطا در تولید محتوا: {str(exc)}",
            })

    return stream


# ─────────────────────────────────────────────
# روت‌های API
# ─────────────────────────────────────────────

@router.post("/articles/generate-stream")
async def generate_stream_post(
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """تولید مقاله با streaming — توصیه‌شده برای UI."""
    return StreamingResponse(
        _build_stream(db, current_user, body.topic, body.keyword, body.llm_model)(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",        # غیرفعال کردن Nginx buffering
            "Access-Control-Allow-Origin": "*", # برای Vercel
        },
    )


@router.get("/articles/generate-stream")
async def generate_stream_get(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    topic: str = Query(..., description="موضوع مقاله"),
    keyword: str = Query(..., description="کلمه کلیدی اصلی"),
    llm_model: str | None = Query(None, description="مدل هوش مصنوعی"),
):
    return StreamingResponse(
        _build_stream(db, current_user, topic, keyword, llm_model)(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/articles/generate", response_model=ArticleResponse)
async def generate_no_stream(
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """تولید مقاله بدون streaming — برای تست مستقیم API."""
    if not _has_api_key():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key تنظیم نشده.",
        )

    model = body.llm_model or _default_model()
    llm = LLMGateway(model=model)
    generator = SEOGenerator(llm)
    critic = SEOCritic(llm)
    researcher = WebResearcher()

    research_data = await researcher.research(body.topic)
    all_facts = _extract_facts(research_data)
    outline = await generator.generate_outline(body.topic, body.keyword, research_data)

    sections = outline.get("sections", [])
    lsi_keywords = outline.get("lsi_keywords", [])
    domain_glossary = outline.get("domain_glossary", {})
    facts_map = distribute_facts_to_sections(sections, all_facts)

    sections_html: list[str] = []
    accumulated_titles = f"عنوان اصلی: {outline.get('h1', body.keyword)}"

    for idx, section in enumerate(sections, start=1):
        if idx > 1 and _SECTION_DELAY > 0:
            await asyncio.sleep(_SECTION_DELAY)

        h2 = section.get("h2", f"بخش {idx}")
        core_thesis = (
            section.get("core_thesis")
            or section.get("content_angle")
            or f"توضیح {h2}"
        )

        html = await generator.draft_section(
            h2_title=h2,
            core_thesis=core_thesis,
            h3_list=section.get("h3_list", []),
            keyword=body.keyword,
            lsi_keywords=lsi_keywords,
            domain_glossary=domain_glossary,
            section_facts=facts_map.get(h2, []),
            written_titles=accumulated_titles,
            required_facts=section.get("required_facts", []),
        )
        sections_html.append(html)
        accumulated_titles += f" | {h2}"

    full_content = _assemble_html(outline, sections_html)
    full_content, score = await _run_seo_audit(critic, full_content, body.keyword)
    article = _save_article(db, outline, full_content, body.keyword, score, current_user.id)
    return article


@router.get("/articles", response_model=list[ArticleResponse])
def list_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    query = db.query(Article)
    if not _can_view_all(current_user):
        query = query.filter(Article.author_id == current_user.id)
    return query.order_by(Article.created_at.desc()).all()


@router.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")
    return article


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
def update_article(
    article_id: int,
    body: ArticleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(article, field, value)

    db.commit()
    db.refresh(article)
    return article


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """حذف مقاله — فقط admin یا صاحب مقاله."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    db.delete(article)
    db.commit()


@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(
    article_id: int,
    body: PublishRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """انتشار مقاله در وردپرس — فقط admin و editor."""
    if not _can_publish(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط admin و editor می‌توانند مقاله منتشر کنند.",
        )

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    if article.status == "published" and article.wp_post_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"این مقاله قبلاً در وردپرس منتشر شده. شناسه پست: {article.wp_post_id}",
        )

    wp_url = body.wp_url or getattr(settings, "WP_URL", "")
    wp_username = body.wp_username or getattr(settings, "WP_USERNAME", "")
    wp_password = body.wp_app_password or getattr(settings, "WP_APP_PASSWORD", "")

    if not all([wp_url, wp_username, wp_password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="اطلاعات وردپرس ناقص است. WP_URL، WP_USERNAME و WP_APP_PASSWORD را تنظیم کنید.",
        )

    credentials = base64.b64encode(f"{wp_username}:{wp_password}".encode()).decode()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts",
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
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="وردپرس پاسخ نداد. لطفاً دوباره تلاش کنید.",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"وردپرس خطا داد: {exc.response.status_code} — {exc.response.text[:200]}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"خطا در اتصال به وردپرس: {str(exc)}",
        ) from exc

    article.wp_post_id = wp_data.get("id")
    article.status = "published"
    db.commit()
    db.refresh(article)
    return article