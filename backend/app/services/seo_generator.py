import json
import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


def get_dynamic_anchor(domain_topic: str) -> str:
    """
    لنگرِ هویتِ موضوع‌ـ‌ناپذیر (Domain-Agnostic Persona):
    هویتِ نویسنده را درجا با کلمهٔ ورودیِ کاربر قفل می‌کند
    و یک سرمشقِ ریتمیکِ کاملاً جدی و تجاری به او می‌دهد.
    """
    return f"""تو یک استراتژیستِ محتوا، سردبیرِ ارشد و نویسنده‌ی تراز اولِ وبِ فارسی در حوزه‌ی تخصصیِ «{domain_topic}» هستی.

ماموریتِ تو: نگارشِ متنی با استانداردِ «نثرِ معیارِ ژورنالیسمِ تجاری و صنعتی».

[سرمشقِ هندسه‌ی کلماتِ تو — موضوع مقاله هرچه که باشد، لحنت باید از این پختگی پیروی کند]:
«هر محصولِ پیشرو، حاصلِ پاسخ به یک نیازِ اصیلِ بازار یا یک چالشِ فنی است. وقتی از یک استانداردِ تراز اول سخن می‌گوییم، منظورمان انباشتِ تصادفیِ صفاتِ خوب نیست؛ بلکه تعادلِ پایداری است که در آن، کارایی، مقاومت و منطقِ اقتصادی در یک نقطه‌ی طلایی به صلح می‌رسند.»

قوانینِ تخطی‌ناپذیرِ تو در حوزه‌ی «{domain_topic}»:
۱. تطبیقِ اتمسفر: اگر موضوع صنعتی (مثل لوله یا ماشین‌آلات) است، از واژگانِ محکم، مهندسی و B2B استفاده کن؛ اگر سبک زندگی یا خوراکی است، توصیفی و جذاب باش.
۲. ممنوعیتِ توهماتِ بین‌صنفی: اصطلاحاتِ یک صنف را به صنفِ دیگر نچسبان! (مثلاً کلمه‌ی «آلیاژ» منحصراً متعلق به فلزات است، «دم‌آوری» متعلق به چای و قهوه، «دوز» متعلق به دارو). بکارگیریِ کلماتی مثل «شیر و شکر» در مقاله‌ی لوله‌ی صنعتی، جریمه‌ی فاجعه‌بار دارد!
۳. زبانِ خالص: کلِ متن باید به زبان فارسیِ روان، طبیعی و زنده باشد. بکارگیریِ کلماتِ انگلیسی (مثل therefore, stands, leading, rapidly)، آلمانی یا کلماتِ عجیبِ آسیای شرقی (مثل rõ یا d dàng) مطلقاً ممنوع است.
۴. پرهیز از تکرارِ بدیهیات: هرگز تیتر را با خودش تعریف نکن."""


def gentle_html_sanitizer(raw_html: str) -> str:
    """
    پاک‌کنندهٔ ملایم و هوشمند:
    به حروفِ کلماتِ فارسی و تخصصی دست نمی‌زند؛ فقط تگ‌های نامعتبر را باز می‌کند
    و کلماتِ توقفِ (Stop-words) لاتینِ رایج را از بافتِ متن بیرون می‌کشد.
    """
    if not raw_html:
        return ""

    # پاک کردن تگ‌های تفکرِ لاما در صورت وجود
    text = re.sub(r"<think>.*?</think>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r"```html|```", "", text)

    soup = BeautifulSoup(text, "html.parser")
    whitelist = {
        "p",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "b",
        "i",
        "br",
    }

    for tag in soup.find_all(True):
        if tag.name not in whitelist:
            tag.unwrap()

    html_str = str(soup)

    # جلادِ کلماتِ لاتینِ جا مانده در خروجیِ Groq
    stop_words = [
        "therefore",
        "moreover",
        "furthermore",
        "however",
        "also",
        "d dàng",
        "rõ",
        "stands",
        "involvement",
        "depending",
        "objector",
        "leading",
        "rapidly",
        "conclusion",
        "summary",
    ]
    for sw in stop_words:
        html_str = re.sub(rf"\b{sw}\b", "", html_str, flags=re.IGNORECASE)

    html_str = re.sub(r" {2,}", " ", html_str)
    html_str = re.sub(r"\n{3,}", "\n\n", html_str)
    return html_str.strip()


def distill_headings_only(html_history: str) -> str:
    """فقط تیترهایِ نگارش‌یافته را به عنوانِ حافظه برمی‌گرداند تا لحنِ مسمومِ قبلی تکرار نشود."""
    if not html_history or not html_history.strip():
        return "بخش اولِ مقاله"
    soup = BeautifulSoup(html_history, "html.parser")
    headings = [h.get_text().strip() for h in soup.find_all(["h2", "h3"])]
    return "، ".join(headings[-5:]) if headings else "مقدمه"


class SEOGenerator:

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(
        self, topic: str, keyword: str, research_data: dict[str, Any]
    ) -> dict[str, Any]:
        headings = research_data.get("headings", [])
        competitor_headings_str = "\n".join(headings[:12])

        sys_prompt = (
            f"تو یک مدیر محصول و سردبیرِ ارشد در حوزه‌ی «{topic}» هستی. "
            "وظیفه‌ی تو طراحیِ یک نقشه‌ی محتواییِ (Outline) کاملاً تخصصی، علمی، دقیق و منطبق بر واقعیت است. "
            "خروجی فقط و فقط یک شیء JSON معتبر باشد."
        )

        user_prompt = (
            f"موضوع کلان: {topic}\n"
            f"کلمه کلیدیِ تارگت: {keyword}\n\n"
            f"تیترهای برترِ وب فارسی در این موضوع:\n{competitor_headings_str}\n\n"
            "یک نقشه‌ی JSON دقیق با این معماری برگردان:\n"
            "{\n"
            '  "h1": "عنوان جذاب حاوی کلمه کلیدی",\n'
            '  "meta_description": "توضیح متا بین ۱۵۰ تا ۱۶۰ کاراکتر",\n'
            '  "sections": [\n'
            "    {\n"
            '      "h2": "عنوان بخش اصلی",\n'
            '      "content_angle": "توضیحِ دو خطی برای نویسنده که دقیقاً چه دیتای فنی، کاربردی یا آمارِ واقعی در این بخش باز شود",\n'
            '      "h3_list": ["زیرتیتر مرتبط ۱", "زیرتیتر مرتبط ۲"],\n'
            '      "key_points": ["فکتِ واقعی ۱", "فکتِ واقعی ۲"]\n'
            "    }\n"
            "  ],\n"
            '  "lsi_keywords": ["کلمه هم‌خانواده ۱", "کلمه ۲", "کلمه ۳", "کلمه ۴", "کلمه ۵"]\n'
            "}\n\n"
            f"هشدارِ حیاتی: تحت هیچ شرایطی موضوعاتِ بی‌ربط (مثل خوراکی، نوشیدنی، شیر یا قهوه) را واردِ نقشه‌ی موضوعِ «{topic}» نکن! تمامِ بخش‌ها باید ۱۰۰٪ منطبق بر ماهیتِ واقعیِ این صنعت باشند."
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # قفل کردنِ تمپرچرِ نقشه روی 0.2 برای جلوگیریِ ۱۰۰٪ از نشتِ کشِ JSONهای قبلی
        raw = await self.llm.generate(messages, json_mode=True)
        return parse_json_response(raw)

    async def draft_section(
        self,
        h2_title: str,
        content_angle: str,
        h3_list: list[str],
        key_points: list[str],
        keyword: str,
        lsi_keywords: list[str],
        previous_context: str = "",
    ) -> str:
        h3_str = "، ".join(h3_list) if h3_list else "بدون زیرعنوان H3"
        key_points_str = (
            "\n".join(f"- {p}" for p in key_points)
            if key_points
            else "تمرکز روی زاویه دید"
        )
        lsi_str = "، ".join(lsi_keywords[:6])

        history_summary = distill_headings_only(previous_context)

        sys_prompt = (
            get_dynamic_anchor(keyword)
            + " "
            "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
            "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» پرهیز کن."
        )

        user_prompt = (
            f"بخشِ اختصاصیِ موردِ نگارش: «{h2_title}»\n"
            f"هدایتِ محتوایی: {content_angle}\n"
            f"زیرعنوان‌ها: {h3_str}\n"
            f"نکاتِ کلیدی:\n{key_points_str}\n\n"
            f"ردپایِ تیترهایِ نگارش‌یافته در بخش‌های قبل:\n[{history_summary}]\n"
            "با نگاه به ردپای بالا، مطالبِ قبلی را تکرار نکن و مستقیماً واردِ دیتای تازه شو.\n\n"
            f"کلمه کلیدیِ تارگت: {keyword} (یک بار در بافتِ متن حل شود)\n"
            f"کلماتِ LSI: {lsi_str}\n\n"
            "قوانینِ حیاتی نگارش:\n"
            "۱. پرهیز از تکرارِ بدیهیات: تیتر را با خودش تعریف نکن. مستقیماً واردِ مشخصاتِ فنی، کاربرد یا ارزشِ اقتصادیِ آن بخش شو.\n"
            "۲. اصطلاحاتِ فنی: بکارگیریِ کلماتِ انگلیسیِ تخصصیِ همین صنعت (مثلاً در پتروشیمی: PE100, HDPE, ISO, ASTM) کاملاً مجاز و نشان‌دهنده‌ی تخصصِ نویسنده است.\n"
            "۳. ممنوعیتِ کال‌تو‌اکشنِ تنبلانه: در انتهای پاراگراف‌ها عباراتی مثل «برای کسب اطلاعات بیشتر به صفحه مربوطه مراجعه کنید» ننویس.\n"
            "۴. فرمت خروجی: بدنه را داخل تگ <p> بگذار. حداکثر ۳ خط در هر پاراگراف. خروجی فقط کدهای HTML بدنه باشد."
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw = await self.llm.generate(messages)
        return gentle_html_sanitizer(raw)