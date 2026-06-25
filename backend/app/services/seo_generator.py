"""
SEO Generator v2 — Grounded Generation
هدف: کاهش hallucination با مدل‌های ضعیف از طریق:
۱. جداسازی facts برای هر بخش (Section-Specific Grounding)
۲. Constraint-based prompting (فقط از facts موجود بنویس)
۳. کوتاه کردن context برای جلوگیری از گم شدن مدل
۴. Fact verification pass قبل از خروجی نهایی
"""
import json
import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


# ─────────────────────────────────────────────
# ۱. فیلتر کاراکترهای بیگانه (فارسی دست‌نخورده)
# ─────────────────────────────────────────────
_ALIEN_FILTER = re.compile(
    r"[\u0900-\u097F"      # هندی
    r"\u4E00-\u9FFF"       # چینی
    r"\u3040-\u30FF"       # ژاپنی
    r"\u0E00-\u0E7F"       # تایلندی
    r"\u0400-\u04FF"       # سیریلیک
    r"\u0500-\u052F]+"     # سیریلیک تکمیلی
)

_HALLUCINATION_PATTERNS = re.compile(
    r"\b(\d{1,3}٪|\d+\s*درصد|\d+\s*میلیون|\d+\s*هزار\s*تومان"
    r"|\d{4}\s*استاندارد|ISO\s*\d+|EN\s*\d+)\b"
)


def sanitize_html(raw: str) -> str:
    """پاکسازی HTML خروجی مدل."""
    if not raw:
        return ""
    # حذف think blocks و markdown fences
    out = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"```html|```", "", out, flags=re.IGNORECASE)
    # حذف کاراکترهای بیگانه
    out = _ALIEN_FILTER.sub("", out)
    # فقط تگ‌های مجاز
    soup = BeautifulSoup(out, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in {"p", "h3", "h4", "ul", "ol", "li", "strong", "em", "br"}:
            tag.unwrap()
    out = str(soup)
    out = re.sub(r" {2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def extract_written_titles(html_history: str) -> str:
    """فقط عناوین نوشته‌شده را برمی‌گرداند — نه کل HTML."""
    if not html_history:
        return "هنوز چیزی نوشته نشده."
    soup = BeautifulSoup(html_history, "html.parser")
    titles = [h.get_text().strip() for h in soup.find_all(["h1", "h2", "h3"])]
    return " | ".join(titles[-5:]) if titles else "هنوز چیزی نوشته نشده."


def flag_unverified_claims(html: str) -> str:
    """
    اعداد و آمار تولید شده توسط مدل را با [نیاز به تأیید] علامت‌گذاری می‌کند.
    این به کاربر هشدار می‌دهد قبل از انتشار بررسی کند.
    """
    return _HALLUCINATION_PATTERNS.sub(
        lambda m: f'<mark title="این عدد را قبل از انتشار تأیید کنید">{m.group()}</mark>',
        html,
    )


# ─────────────────────────────────────────────
# ۲. توزیع facts به بخش‌های مرتبط
# ─────────────────────────────────────────────
def distribute_facts_to_sections(
    sections: list[dict], all_facts: list[str]
) -> dict[str, list[str]]:
    """
    هر fact را به مرتبط‌ترین بخش نسبت می‌دهد.
    جلوگیری از دادن یک facts یکسان به همه بخش‌ها.
    """
    result: dict[str, list[str]] = {s.get("h2", ""): [] for s in sections}

    for fact in all_facts:
        best_section = None
        best_score = 0
        fact_words = set(fact.replace("،", " ").replace(".", " ").split())

        for section in sections:
            h2 = section.get("h2", "")
            thesis = section.get("core_thesis", "")
            section_words = set((h2 + " " + thesis).split())
            score = len(fact_words & section_words)
            if score > best_score:
                best_score = score
                best_section = h2

        if best_section and best_score > 0:
            result[best_section].append(fact)
        elif sections:
            # اگه مطابقتی نبود به اولین بخش بده
            result[sections[0].get("h2", "")].append(fact)

    return result


# ─────────────────────────────────────────────
# ۳. کلاس اصلی
# ─────────────────────────────────────────────
class SEOGenerator:

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(
        self, topic: str, keyword: str, research_data: dict[str, Any]
    ) -> dict[str, Any]:
        headings = research_data.get("headings", [])

        messages = [
            {
                "role": "system",
                "content": (
                    f"تو یک معمار محتوای سئو در حوزه «{topic}» هستی. "
                    "خروجی: فقط JSON معتبر، بدون توضیح اضافه، تمام مقادیر فارسی."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"موضوع: {topic}\n"
                    f"کلمه کلیدی: {keyword}\n"
                    f"تیترهای رقبا (برای الهام): {', '.join(headings[:8])}\n\n"
                    "JSON با این ساختار دقیق:\n"
                    "{\n"
                    '  "h1": "عنوان حاوی کلمه کلیدی",\n'
                    '  "meta_description": "۱۵۰ تا ۱۶۰ کاراکتر فارسی",\n'
                    '  "domain_glossary": {"اصطلاح_انگلیسی": "معادل_فارسی"},\n'
                    '  "sections": [\n'
                    "    {\n"
                    '      "h2": "عنوان بخش",\n'
                    '      "core_thesis": "یک جمله توضیح این بخش — چه سوالی جواب می‌دهد؟",\n'
                    '      "h3_list": ["زیرعنوان ۱", "زیرعنوان ۲"],\n'
                    '      "required_facts": ["چه نوع اطلاعاتی برای این بخش لازم است؟"]\n'
                    "    }\n"
                    "  ],\n"
                    '  "lsi_keywords": ["کلمه مرتبط ۱", "کلمه ۲", "کلمه ۳"]\n'
                    "}\n\n"
                    "قوانین:\n"
                    "- ۵ تا ۶ بخش H2\n"
                    "- هر H2 منحصربه‌فرد باشد\n"
                    "- core_thesis یک جمله واضح باشد، نه کلی‌گویی\n"
                    "- required_facts مشخص کند این بخش به چه داده‌ای نیاز دارد"
                ),
            },
        ]

        raw = await self.llm.generate(messages, json_mode=True)
        return parse_json_response(raw)

    async def draft_section(
        self,
        h2_title: str,
        core_thesis: str,
        h3_list: list[str],
        keyword: str,
        lsi_keywords: list[str],
        domain_glossary: dict[str, str],
        section_facts: list[str],      # facts اختصاصی این بخش
        written_titles: str = "",       # فقط عناوین، نه کل HTML
        required_facts: list[str] = [], # چه نوع اطلاعاتی نیاز است
    ) -> str:

        # اگه fact کافی نداریم، به مدل صراحتاً بگو
        if len(section_facts) < 2:
            facts_instruction = (
                "⚠️ هشدار: اطلاعات کافی از جستجوی وب برای این بخش پیدا نشد.\n"
                "فقط اطلاعاتی بنویس که قطعاً درست است.\n"
                "از اعداد، آمار یا ادعاهای خاص بدون منبع پرهیز کن.\n"
                "اگه چیزی نمی‌دانی، به جای ساختن، بگو «برای اطلاعات دقیق‌تر با متخصص مشورت کنید»."
            )
            facts_str = "اطلاعات کافی از وب پیدا نشد."
        else:
            facts_instruction = (
                "فقط از این اطلاعات تأییدشده استفاده کن. "
                "چیزی اضافه نکن که در این facts نیست."
            )
            facts_str = "\n".join(f"• {f}" for f in section_facts[:6])

        h3_str = "، ".join(h3_list) if h3_list else "ندارد"
        lsi_str = "، ".join(lsi_keywords[:5])
        glossary_note = (
            "اصطلاحات تخصصی این حوزه: "
            + "، ".join(f"{en}={fa}" for en, fa in list(domain_glossary.items())[:4])
            if domain_glossary else ""
        )

        messages = [
            {
                "role": "system",
                "content": (
                    f"تو یک نویسنده محتوای فارسی در حوزه «{keyword}» هستی.\n"
                    "قوانین اساسی:\n"
                    "۱. فقط به زبان فارسی بنویس\n"
                    "۲. فقط از اطلاعات داده‌شده استفاده کن — چیزی نساز\n"
                    "۳. اگه اطلاعاتی نداری، ننویس\n"
                    "۴. عنوان H2 را تکرار نکن\n"
                    "۵. خروجی فقط HTML با تگ‌های <p> و <h3>"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"بخش: «{h2_title}»\n"
                    f"هدف این بخش: {core_thesis}\n"
                    f"زیرعنوان‌ها: {h3_str}\n\n"
                    f"=== اطلاعات تأییدشده برای این بخش ===\n"
                    f"{facts_str}\n"
                    f"==========================================\n\n"
                    f"{facts_instruction}\n\n"
                    f"عناوینی که قبلاً نوشته‌ام: [{written_titles}]\n"
                    "مطالب این عناوین را تکرار نکن.\n\n"
                    f"کلمه کلیدی (یک بار استفاده): {keyword}\n"
                    f"کلمات مرتبط: {lsi_str}\n"
                    f"{glossary_note}\n\n"
                    "مشخصات متن:\n"
                    "- ۱۲۰ تا ۲۰۰ کلمه\n"
                    "- هر جمله زیر ۲۵ کلمه\n"
                    "- هر پاراگراف حداکثر ۳ خط"
                ),
            },
        ]

        raw = await self.llm.generate(messages)
        html = sanitize_html(raw)
        # علامت‌گذاری اعداد و آمار برای تأیید کاربر
        return flag_unverified_claims(html)