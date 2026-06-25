import json
import re
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

# فیلتر کاراکترهای بیگانه (حذف زبان‌های شرقی و سیریلیک، آزاد گذاشتن فارسی و انگلیسی)
_ALIEN_FILTER = re.compile(
    r"[\u0900-\u097F\u4E00-\u9FFF\u3040-\u30FF\u0E00-\u0E7F\u0400-\u04FF\u0500-\u052F]+"
)

@dataclass
class ArticleState:
    """
    حافظه مرکزی و مدیر وضعیت مقاله.
    این شیء در کل چرخه حیات مقاله همراه ماست و جلوی تکرار مفاهیم را می‌گیرد.
    """
    topic: str
    keyword: str
    research_data: dict = field(default_factory=dict)
    all_facts: list[str] = field(default_factory=list)
    outline: dict = field(default_factory=dict)
    facts_map: dict = field(default_factory=dict)
    sections_html: list[str] = field(default_factory=list)
    completed_theses: list[str] = field(default_factory=list)
    
    def get_narrative_memory(self) -> str:
        if not self.completed_theses:
            return "این اولین بخش مقاله است. یک شروع جذاب بنویس و مستقیماً وارد بحث اصلی شو."
        
        # استخراج مفاهیم گفته شده در بخش‌های قبل به جای کلمات خام
        memory = " | ".join(self.completed_theses)
        return (
            f"⚠️ توجه بسیار مهم: مفاهیم و نتیجه‌گیری‌های زیر در بخش‌های قبلی مقاله به طور کامل بیان شده‌اند:\n"
            f"[{memory}]\n\n"
            "قانونِ عدم تکرارِ مفهومی: به هیچ وجه استدلال‌ها، نتیجه‌گیری‌ها یا مقدمه‌های بالا را در این بخش تکرار نکن. "
            "نیازی نیست برای جلوگیری از تکرار، به دنبال مترادف‌های عجیب بگردی! راه حل درست این است که "
            "مستقیماً و منحصراً درباره‌ی دیتایِ جدیدِ همین تیتر صحبت کنی."
        )


def sanitize_html(raw: str) -> str:
    """پاکسازی HTML با پشتیبانی از تگ‌های غنی و حذف مارک‌دان‌های مزاحم."""
    if not raw:
        return ""

    out = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"\x60{3}html|\x60{3}", "", out, flags=re.IGNORECASE)
    
    # حذف کاراکترهای مارک‌دان (مثل ## و ###) که به اشتباه چاپ شده‌اند
    out = re.sub(r"(?m)^#{1,6}\s*", "", out)
    
    out = _ALIEN_FILTER.sub("", out)

    soup = BeautifulSoup(out, "html.parser")
    valid_tags = {
        "p", "h3", "h4", "ul", "ol", "li", "strong", "em", "br",
        "table", "thead", "tbody", "tr", "th", "td", "blockquote"
    }
    for tag in soup.find_all(True):
        if tag.name not in valid_tags:
            tag.unwrap()

    out = str(soup)
    out = re.sub(r" {2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def fast_seo_scorer(html: str, keyword: str) -> int:
    """ارزیاب آفلاین، فوق‌سریع و مبتنی بر Constraint برای سئو."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    words = text.split()
    word_count = len(words)

    score = 40

    h1_tag = soup.find("h1")
    if h1_tag:
        score += 15
        if keyword in h1_tag.get_text():
            score += 10

    if soup.find("h2"):
        score += 10

    kw_count = text.count(keyword)
    if word_count > 0:
        density = (kw_count / word_count) * 100
        if 0.5 <= density <= 2.5:
            score += 15
        elif density > 0:
            score += 5

    if word_count > 800:
        score += 10
    elif word_count > 400:
        score += 5

    return min(score, 100)


class SEOGenerator:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(self, topic: str, keyword: str, research_data: dict[str, Any]) -> dict[str, Any]:
        headings = research_data.get("headings", [])
        messages = [
            {
                "role": "system",
                "content": (
                    f"تو یک معمار محتوای سئو در حوزه «{topic}» هستی. "
                    "خروجی: فقط JSON معتبر، تمام مقادیر فارسی (مگر اصطلاحات تخصصی)."
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
                    "- ۵ تا ۷ بخش H2\n"
                    "- هر H2 کاملاً متفاوت با بقیه باشد\n"
                    "- core_thesis یک جمله تحلیلی و واضح باشد"
                ),
            },
        ]
        raw = await self.llm.generate(messages, json_mode=True)
        return parse_json_response(raw)

    async def distribute_facts_semantic(self, sections: list[dict], facts: list[str]) -> dict[str, list[str]]:
        if not facts or not sections:
            return {s.get("h2", ""): [] for s in sections}

        facts_dict = {str(i): f for i, f in enumerate(facts)}
        section_titles = [s.get("h2", "") for s in sections]

        prompt = (
            "نقش تو یک دستیار پژوهشگر است.\n"
            "لیستی از فکت‌ها (با شناسه عددی) و لیستی از تیترهای یک مقاله به تو داده می‌شود.\n"
            "وظیفه تو اختصاص دادن هر فکت به مرتبط‌ترین تیتر است.\n"
            "خروجی منحصراً یک JSON با این فرمت باشد:\n"
            "{\n"
            '  "عنوان تیتر اول": [0, 3, 5],\n'
            '  "عنوان تیتر دوم": [1, 2]\n'
            "}\n"
            "اگر فکتی به هیچ تیتری نمی‌خورد، آن را نادیده بگیر."
        )

        user_msg = (
            f"تیترها:\n{json.dumps(section_titles, ensure_ascii=False)}\n\n"
            f"فکت‌ها:\n{json.dumps(facts_dict, ensure_ascii=False)}"
        )

        try:
            raw_json = await self.llm.generate([
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg}
            ], json_mode=True)
            mapping = parse_json_response(raw_json)

            result = {title: [] for title in section_titles}
            for title, indices in mapping.items():
                if title in result and isinstance(indices, list):
                    for idx in indices:
                        if str(idx) in facts_dict:
                            result[title].append(facts_dict[str(idx)])
            return result
        except Exception:
            return {s.get("h2", ""): facts for s in sections}

    async def draft_section_stream(
        self,
        h2_title: str,
        core_thesis: str,
        h3_list: list[str],
        keyword: str,
        lsi_keywords: list[str],
        domain_glossary: dict[str, str],
        section_facts: list[str],
        narrative_memory: str = "",
    ) -> AsyncGenerator[str, None]:
        
        if len(section_facts) == 0:
            facts_instruction = (
                "⚠️ هشدار: فکتِ مستندی برای این بخش یافت نشد.\n"
                "قانون: این بخش را بسیار کوتاه بنویس و منحصراً به بدیهیاتِ اثبات‌شده‌ی این صنعت تکیه کن. "
                "تحت هیچ شرایطی آمار، نام شرکت‌ها یا ادعاهای قطعی تخیل نکن."
            )
            facts_str = "داده‌یِ اختصاصی وجود ندارد. به مفاهیم پایه‌یِ صنعت تکیه کن."
        else:
            facts_instruction = (
                "قانونِ استناد (Grounding): منحصراً از فکت‌هایِ بالا به عنوان مواد خامِ علمی استفاده کن. "
                "تخیل کردنِ آمار و ارقام مطلقاً ممنوع است."
            )
            facts_str = "\n".join(f"• {f}" for f in section_facts[:6])

        h3_str = "، ".join(h3_list) if h3_list else "ندارد"
        lsi_str = "، ".join(lsi_keywords[:5])
        glossary_note = (
            "ترجمه‌ی اصطلاحات (الزامی): "
            + "، ".join(f"{en}={fa}" for en, fa in list(domain_glossary.items())[:4])
            if domain_glossary else "مجاز به استفاده از اصطلاحاتِ استانداردِ انگلیسی هستی."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    f"تو یک متخصصِ محتوایِ B2B و کارشناس سئو در حوزه «{keyword}» هستی.\n"
                    "قوانینِ معماری و نگارش:\n"
                    "۱. کلمه کلیدی را ۱ یا ۲ بار در متن کاملاً طبیعی استفاده کن.\n"
                    "۲. عنوان H2 را در خط اول پاراگراف تکرار نکن.\n"
                    "۳. برای جلوگیری از سکته‌های گرامری، طول جملات را استاندارد نگه دار (پرهیز از افعال مرکب پی‌درپی).\n"
                    "۴. متن را با یک نتیجه‌گیریِ بیهوده تمام نکن. مستقیماً در قلبِ موضوع توقف کن.\n"
                    "۵. حتماً جمله‌ی آخر را با نقطه (.) ببند و متن را نیمه‌کاره رها نکن.\n"
                    "۶. خروجی فقط تگ‌های مجاز HTML است. از نوشتنِ کاراکترهای مارک‌دان مثل ## خودداری کن."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"بخشِ تحتِ نگارش: «{h2_title}»\n"
                    f"تزِ مرکزی این بخش: {core_thesis}\n"
                    f"زیرعنوان‌ها: {h3_str}\n\n"
                    f"=== فکت‌هایِ تأییدشده ===\n"
                    f"{facts_str}\n"
                    f"=========================\n"
                    f"{facts_instruction}\n\n"
                    f"=== حافظه‌یِ رواییِ مقاله ===\n"
                    f"{narrative_memory}\n"
                    f"============================\n\n"
                    f"کلمه کلیدیِ هدف: {keyword}\n"
                    f"کلماتِ مرتبط سئو (LSI): {lsi_str}\n"
                    f"{glossary_note}\n\n"
                    "متنِ این بخش را با نثری فاخر و تحلیلی بنویس."
                ),
            },
        ]

        stream_gen = await self.llm.generate(messages, stream=True)
        async for chunk in stream_gen:
            yield chunk

    async def draft_section(self, *args, **kwargs) -> str:
        accumulated_html = ""
        async for chunk in self.draft_section_stream(*args, **kwargs):
            accumulated_html += chunk
        return sanitize_html(accumulated_html)