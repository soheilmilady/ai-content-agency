import asyncio
import base64
import json
import logging
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
from app.services.seo_generator import (
    SEOGenerator,
    ArticleState,
    fast_seo_scorer,
    sanitize_html
)
from app.services.web_researcher import WebResearcher

logger = logging.getLogger(__name__)
router = APIRouter()

_SECTION_DELAY: float = float(getattr(settings, "SECTION_DELAY_SECONDS", "3.0"))


# ─────────────────────────────────────────────
# توابع کمکی دسترسی و امنیتی
# ─────────────────────────────────────────────

def _can_view_all(user: User) -> bool:
    return user.role in ("admin", "editor")

def _can_access(user: User, article: Article) -> bool:
    return _can_view_all(user) or article.author_id == user.id

def _can_publish(user: User) -> bool:
    return user.role in ("admin", "editor")

def _has_api_key() -> bool:
    return bool(
        getattr(settings, "GROQ_API_KEY", None)
        or getattr(settings, "OPENROUTER_API_KEY", None)
    )

def _default_model() -> str:
    if getattr(settings, "GROQ_API_KEY", None):
        return "groq/llama-3.3-70b-versatile"
    return getattr(settings, "DEFAULT_LLM_MODEL", "openai/gpt-4o-mini")

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def _assemble_html(state: ArticleState) -> str:
    parts = [f"<h1>{state.outline.get('h1', state.keyword)}</h1>"]
    for section, html in zip(state.outline.get("sections", []), state.sections_html):
        h2 = section.get("h2", "")
        if h2:
            parts.append(f"<h2>{h2}</h2>")
        if html:
            parts.append(html)
    return "".join(parts)


# ─────────────────────────────────────────────
# کلاس ارکستراتور (مدیریت جریان تولید محتوا)
# ─────────────────────────────────────────────

class ArticlePipeline:
    """ارکستراتور مرکزی که شیء ArticleState را در طول مراحل پردازش هدایت می‌کند."""
    
    def __init__(self, db: Session, current_user: User, llm_model: str | None):
        self.db = db
        self.current_user = current_user
        self.model = llm_model or _default_model()
        self.llm = LLMGateway(model=self.model)
        self.generator = SEOGenerator(self.llm)
        self.researcher = WebResearcher()

    def _extract_facts(self, research_data: dict) -> list[str]:
        snippets = research_data.get("snippets", [])
        if isinstance(snippets, list) and snippets:
            return [s for s in snippets if isinstance(s, str) and len(s) > 20]
        content = research_data.get("content", "")
        if isinstance(content, str) and content:
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20]
            return sentences[:15]
        return []

    def _save_article(self, state: ArticleState, full_content: str, score: int) -> Article:
        article = Article(
            title=state.outline.get("h1", state.keyword),
            content_html=full_content,
            meta_description=state.outline.get("meta_description", "")[:160],
            focus_keyword=state.keyword,
            seo_score=score,
            status="pending_approval",
            author_id=self.current_user.id,
        )
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    async def execute_stream(self, topic: str, keyword: str) -> AsyncGenerator[str, None]:
        try:
            if not _has_api_key():
                yield _sse({"step": "error", "message": "کلید API تنظیم نشده است."})
                return

            # ۱. مقداردهی اولیه State
            state = ArticleState(topic=topic, keyword=keyword)

            # ۲. فاز تحقیق
            yield _sse({"step": "researching", "message": "در حال تحقیق زنده..."})
            state.research_data = await self.researcher.research(topic)
            state.all_facts = self._extract_facts(state.research_data)

            # ۳. فاز طراحی ساختار (Outline)
            yield _sse({"step": "outlining", "message": "در حال طراحی ساختار..."})
            state.outline = await self.generator.generate_outline(topic, keyword, state.research_data)

            sections = state.outline.get("sections", [])
            lsi_keywords = state.outline.get("lsi_keywords", [])
            domain_glossary = state.outline.get("domain_glossary", {})
            total = len(sections)

            # ۴. فاز نگاشت فکت‌ها
            yield _sse({"step": "routing_facts", "message": "تخصیص هوشمند اطلاعات..."})
            state.facts_map = await self.generator.distribute_facts_semantic(sections, state.all_facts)

            # ارسال H1 به فرانت‌اند
            yield _sse({"token": f"<h1>{state.outline.get('h1', keyword)}</h1>\n\n"})

            # ۵. فاز نگارش بخش به بخش
            for idx, section in enumerate(sections, start=1):
                h2 = section.get("h2", f"بخش {idx}")
                yield _sse({
                    "step": "drafting",
                    "message": f"نگارش بخش {idx} از {total}: «{h2}»",
                    "progress": round((idx - 1) / total * 100),
                })

                if idx > 1 and _SECTION_DELAY > 0:
                    await asyncio.sleep(_SECTION_DELAY)

                yield _sse({"token": f"<h2>{h2}</h2>\n"})

                core_thesis = section.get("core_thesis") or section.get("content_angle") or f"توضیح {h2}"
                section_facts = state.facts_map.get(h2, [])
                
                # فراخوانیِ حافظه‌ی مفهومی
                narrative_memory = state.get_narrative_memory()

                accumulated_section_html = ""
                stream_generator = self.generator.draft_section_stream(
                    h2_title=h2,
                    core_thesis=core_thesis,
                    h3_list=section.get("h3_list", []),
                    keyword=state.keyword,
                    lsi_keywords=lsi_keywords,
                    domain_glossary=domain_glossary,
                    section_facts=section_facts,
                    narrative_memory=narrative_memory,
                )

                async for chunk in stream_generator:
                    accumulated_section_html += chunk
                    yield _sse({"token": chunk})

                yield _sse({"token": "\n\n"})

                clean_html = sanitize_html(accumulated_section_html)
                state.sections_html.append(clean_html)
                
                # ثبت تز مرکزیِ این بخش در حافظه برای جلوگیری از تکرار در بخش‌های بعد
                state.completed_theses.append(core_thesis)

                yield _sse({
                    "step": "section_ready",
                    "index": idx,
                    "total": total,
                    "h2": h2,
                    "html": clean_html,
                    "facts_used": len(section_facts),
                })

            # ۶. فاز ارزیابی آفلاین سئو
            yield _sse({"step": "auditing", "message": "محاسبه امتیاز سئو..."})
            full_content = _assemble_html(state)
            score = fast_seo_scorer(full_content, keyword)

            # ۷. ذخیره‌سازی نهایی
            article = self._save_article(state, full_content, score)

            yield _sse({
                "step": "done",
                "article_id": article.id,
                "seo_score": score,
                "title": article.title,
                "meta_description": state.outline.get("meta_description", ""),
                "facts_total": len(state.all_facts),
            })

        except asyncio.TimeoutError:
            logger.error("Timeout during streaming", exc_info=True)
            yield _sse({"step": "error", "message": "زمان پاسخ مدل تمام شد. لطفاً دوباره تلاش کنید."})
        except Exception as exc:
            logger.error(f"Generation stream error: {exc}", exc_info=True)
            yield _sse({"step": "error", "message": "یک خطای داخلی در سرور رخ داد. تیم فنی مطلع شد."})

    async def execute_no_stream(self, topic: str, keyword: str) -> Article:
        if not _has_api_key():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API key تنظیم نشده.")
        
        state = ArticleState(topic=topic, keyword=keyword)
        state.research_data = await self.researcher.research(topic)
        state.all_facts = self._extract_facts(state.research_data)
        state.outline = await self.generator.generate_outline(topic, keyword, state.research_data)
        
        sections = state.outline.get("sections", [])
        lsi_keywords = state.outline.get("lsi_keywords", [])
        domain_glossary = state.outline.get("domain_glossary", {})
        state.facts_map = await self.generator.distribute_facts_semantic(sections, state.all_facts)

        for idx, section in enumerate(sections, start=1):
            if idx > 1 and _SECTION_DELAY > 0:
                await asyncio.sleep(_SECTION_DELAY)

            h2 = section.get("h2", f"بخش {idx}")
            core_thesis = section.get("core_thesis") or section.get("content_angle") or f"توضیح {h2}"
            
            html = await self.generator.draft_section(
                h2_title=h2,
                core_thesis=core_thesis,
                h3_list=section.get("h3_list", []),
                keyword=state.keyword,
                lsi_keywords=lsi_keywords,
                domain_glossary=domain_glossary,
                section_facts=state.facts_map.get(h2, []),
                narrative_memory=state.get_narrative_memory(),
            )
            state.sections_html.append(html)
            state.completed_theses.append(core_thesis)

        full_content = _assemble_html(state)
        score = fast_seo_scorer(full_content, keyword)
        return self._save_article(state, full_content, score)


# ─────────────────────────────────────────────
# روت‌های API
# ─────────────────────────────────────────────

@router.post("/articles/generate-stream")
async def generate_stream_post(
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    pipeline = ArticlePipeline(db, current_user, body.llm_model)
    return StreamingResponse(
        pipeline.execute_stream(body.topic, body.keyword),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )

@router.get("/articles/generate-stream")
async def generate_stream_get(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    topic: str = Query(...),
    keyword: str = Query(...),
    llm_model: str | None = Query(None),
):
    pipeline = ArticlePipeline(db, current_user, llm_model)
    return StreamingResponse(
        pipeline.execute_stream(topic, keyword),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.post("/articles/generate", response_model=ArticleResponse)
async def generate_no_stream(
    body: GenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        pipeline = ArticlePipeline(db, current_user, body.llm_model)
        return await pipeline.execute_no_stream(body.topic, body.keyword)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Generation error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="خطای داخلی در تولید محتوا.")

@router.get("/articles", response_model=list[ArticleResponse])
def list_articles(db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    query = db.query(Article)
    if not _can_view_all(current_user):
        query = query.filter(Article.author_id == current_user.id)
    return query.order_by(Article.created_at.desc()).all()

@router.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")
    return article

@router.patch("/articles/{article_id}", response_model=ArticleResponse)
def update_article(article_id: int, body: ArticleUpdate, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
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
def delete_article(article_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    db.delete(article)
    db.commit()

@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(article_id: int, body: PublishRequest, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    if not _can_publish(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط admin و editor می‌توانند مقاله منتشر کنند.")

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مقاله یافت نشد.")
    if not _can_access(current_user, article):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی ندارید.")

    if article.status == "published" and article.wp_post_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"این مقاله قبلاً در وردپرس منتشر شده. شناسه پست: {article.wp_post_id}")

    wp_url = body.wp_url or getattr(settings, "WP_URL", "")
    wp_username = body.wp_username or getattr(settings, "WP_USERNAME", "")
    wp_password = body.wp_app_password or getattr(settings, "WP_APP_PASSWORD", "")

    if not all([wp_url, wp_username, wp_password]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اطلاعات وردپرس ناقص است.")

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
    except Exception as exc:
        logger.error(f"WordPress publish error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="خطا در اتصال به وردپرس. به تیم فنی اطلاع داده شد.")

    article.wp_post_id = wp_data.get("id")
    article.status = "published"
    db.commit()
    db.refresh(article)
    return article