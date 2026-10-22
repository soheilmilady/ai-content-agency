import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.article import Article
from app.models.user import User
from app.services.llm_gateway import LLMGateway
from app.services.seo_generator import (
    ArticleState,
    SEOGenerator,
    fast_seo_scorer,
    sanitize_html,
)
from app.services.web_researcher import WebResearcher

logger = logging.getLogger(__name__)

_SECTION_DELAY: float = float(getattr(settings, "SECTION_DELAY_SECONDS", "3.0"))


def has_llm_api_key() -> bool:
    """بررسی وجود حداقل یک کلید API معتبر برای هوش مصنوعی."""
    return bool(
        getattr(settings, "GEMINI_API_KEY", None)
        or getattr(settings, "GROQ_API_KEY", None)
        or getattr(settings, "OPENROUTER_API_KEY", None)
    )


def get_default_llm_model() -> str:
    """دریافت مدل پیش‌فرض پایدار سیستم."""
    return getattr(settings, "DEFAULT_LLM_MODEL", "gemini-3.7-flash")


def _sse(data: dict) -> str:
    """قالب‌بندی داده‌های استریم بر اساس استاندارد Server-Sent Events."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _assemble_html(state: ArticleState) -> str:
    """تجمیع بخش‌های مختلف مقاله به صورت کد HTML نهایی."""
    parts = [f"<h1>{state.outline.get('h1', state.keyword)}</h1>"]
    for section, html in zip(state.outline.get("sections", []), state.sections_html):
        h2 = section.get("h2", "")
        if h2:
            parts.append(f"<h2>{h2}</h2>")
        if html:
            parts.append(html)
    return "".join(parts)


class ArticlePipeline:
    """ارکستراتور مرکزی که شیء ArticleState را در طول مراحل پردازش هدایت می‌کند."""

    def __init__(self, db: Session, current_user: User, llm_model: str | None = None):
        self.db = db
        self.current_user = current_user
        self.model = llm_model or get_default_llm_model()
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

    async def execute_stream(
        self, topic: str, keyword: str, h2_keywords: list[str] | None = None
    ) -> AsyncGenerator[str, None]:
        try:
            if not has_llm_api_key():
                yield _sse({"step": "error", "message": "کلید API تنظیم نشده است."})
                return

            # ۱. مقداردهی اولیه State
            state = ArticleState(topic=topic, keyword=keyword)

            # ۲. فاز تحقیق
            yield _sse({"step": "researching", "message": "در حال تحقیق زنده..."})
            state.research_data = await self.researcher.research(topic)
            raw_facts = self._extract_facts(state.research_data)

            # پاکسازی و اعتبارسنجی فکت‌ها (فاز ۳)
            yield _sse({"step": "validating_facts", "message": "در حال پالایش و اعتبارسنجی اطلاعات..."})
            state.all_facts = await self.generator.validate_and_deduplicate_facts(raw_facts)

            # ۳. فاز طراحی ساختار (Outline)
            yield _sse({"step": "outlining", "message": "در حال طراحی ساختار..."})
            state.outline = await self.generator.generate_outline(topic, keyword, state.research_data, h2_keywords)

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
            user_msg = (
                str(exc)
                if isinstance(exc, ValueError)
                else "یک خطای داخلی در سرور رخ داد. لطفاً دوباره تلاش کنید."
            )
            yield _sse({"step": "error", "message": user_msg})

    async def execute_no_stream(
        self, topic: str, keyword: str, h2_keywords: list[str] | None = None
    ) -> Article:
        if not has_llm_api_key():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API key تنظیم نشده."
            )

        state = ArticleState(topic=topic, keyword=keyword)
        state.research_data = await self.researcher.research(topic)
        raw_facts = self._extract_facts(state.research_data)
        state.all_facts = await self.generator.validate_and_deduplicate_facts(raw_facts)

        state.outline = await self.generator.generate_outline(
            topic, keyword, state.research_data, h2_keywords
        )

        sections = state.outline.get("sections", [])
        lsi_keywords = state.outline.get("lsi_keywords", [])
        domain_glossary = state.outline.get("domain_glossary", {})
        state.facts_map = await self.generator.distribute_facts_semantic(
            sections, state.all_facts
        )

        for idx, section in enumerate(sections, start=1):
            if idx > 1 and _SECTION_DELAY > 0:
                await asyncio.sleep(_SECTION_DELAY)

            h2 = section.get("h2", f"بخش {idx}")
            core_thesis = (
                section.get("core_thesis")
                or section.get("content_angle")
                or f"توضیح {h2}"
            )

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
