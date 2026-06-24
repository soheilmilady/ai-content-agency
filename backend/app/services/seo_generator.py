import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


def get_persian_anchor(domain_subject: str) -> str:
    """
    کهن‌الگوی سیال:
    لحنِ فاخر و ژورنالیستی را بدونِ قفل شدن روی یک موضوع خاص (مثل قهوه) تولید می‌کند
    و هویتِ هوش مصنوعی را به صورتِ شناور با کلمهٔ ورودیِ کاربر هم‌گام می‌سازد.
    """
    return f"""تو یک سردبیرِ ارشد، ژورنالیستِ صاحب‌سبک و استراتژیستِ محتوای وب در حوزه‌ی تخصصیِ «{domain_subject}» هستی.

ماموریتِ تو: نگارشِ متنی با استانداردِ «نثرِ معیارِ ژورنالیسمِ تحلیلی و تجاری».

[سرمشقِ ریتم و هندسه‌ی کلماتِ تو — موضوع مقاله هرچه که باشد، بافتِ جملاتت باید از این معماریِ متین پیروی کند]:
«هر پدیده‌ی پیشرو، حاصلِ پاسخ به یک چالشِ فنی یا نیازِ اصیلِ انسانی است. وقتی از یک استانداردِ تراز اول سخن می‌گوییم، منظورمان انباشتِ تصادفیِ صفاتِ خوب نیست؛ بلکه تعادلِ پایداری است که در آن، کارایی، دوام و منطقِ اقتصادی در یک نقطه‌ی طلایی به صلح می‌رسند. در چنین سطحی از بلوغ، جزئیاتِ محصول دیگر یک «امکانِ اضافه» نیستند، بلکه خودِ هویتِ آن را تعریف می‌کنند.»

قوانینِ بنیادینِ تو در حوزه‌ی «{domain_subject}»:
۱. کالیبراسیونِ لحن: اتمسفرِ کلماتت باید کاملاً با صنعتِ «{domain_subject}» هم‌خوان باشد. اگر موضوع صنعتی یا B2B است، از واژگانِ محکم، مهندسی و تجاری استفاده کن؛ اگر سبک زندگی یا پزشکی است، صمیمی، علمی و توصیفی باش؛ اگر تکنولوژی است، مدرن و تحلیلی.
۲. طردِ کاملِ توهماتِ صنفی (No Cross-Industry Hallucinations): کلماتی مثل «آلیاژ» منحصراً متعلق به فلزاتند، «دم‌آوری» متعلق به نوشیدنی‌های گرم، «دوز» متعلق به دارو، «کامپایل» متعلق به نرم‌افزار. هرگز اصطلاحِ تخصصیِ یک صنف را به زور به صنفِ دیگر نچسبان!
۳. ممنوعیتِ تعاریفِ بدیهی (Anti-Tautology): هرگز یک مفهوم را با تکرارِ اسمِ خودش توضیح نده (مثلاً برای بخشِ «نصب و راه‌اندازی» ننویس: راه‌اندازی مرحله‌ای است که محصول را راه‌اندازی می‌کنیم). مستقیماً واردِ فوتِ کوزه‌گری، استانداردها یا چراییِ آن موضوع شو.
۴. خلوصِ مطلقِ زبانِ فارسی: متن باید ۱۰۰٪ فارسیِ پاک باشد. استفاده از کلماتِ لاتین، آلمانی، یا الفبای شرقی ممنوع است."""


_ALIEN_SCRIPTS = re.compile(
    r"[\u0900-\u097F"  # هندی / سانسکریت
    r"\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF"  # کانجی / چینی / ژاپنی
    r"\u0E00-\u0E7F"  # تایلندی
    r"\u0400-\u04FF"  # روسی / سیریلیک
    r"ạảăắằẳẵặâấầẩẫậẹẻẽêềếểễệỉịọỏôốồổỗộơớờởỡợụủưứừửữựỵỷỹĐđ"  # حروف تن‌دارِ ویتنامی
    r"]+"
)

# کلماتِ توقفِ (Stop-words) لاتین که LLMها عادت دارند وسطِ متنِ استدلالی پرتاب کنند
_KNOWN_FOREIGN_WORDS = re.compile(
    r"\b(drinking|prepare|zwischen|also|however|moreover|furthermore|phổ biến|involvement|depending|objector|summary|conclusion)\b",
    re.IGNORECASE,
)


def sanitize_html_for_tiptap(raw_html: str) -> str:
    text = _KNOWN_FOREIGN_WORDS.sub("", raw_html)
    text = _ALIEN_SCRIPTS.sub("", text)

    soup = BeautifulSoup(text, "html.parser")

    allowed_tags = {
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
        if tag.name not in allowed_tags:
            tag.unwrap()

    output = str(soup)
    output = re.sub(r" {2,}", " ", output)
    output = re.sub(r"\n{3,}", "\n\n", output)
    return output.strip()


def distill_memory(raw_html_memory: str) -> str:
    if not raw_html_memory or not raw_html_memory.strip():
        return "مقاله تازه شروع شده است."

    soup = BeautifulSoup(raw_html_memory, "html.parser")
    headings = [h.get_text().strip() for h in soup.find_all(["h1", "h2", "h3"])]

    if not headings:
        return "مقدماتِ اولیه گفته شده."

    return "، ".join(headings)


class SEOGenerator:

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(
        self, topic: str, keyword: str, research_data: dict[str, Any]
    ) -> dict[str, Any]:
        headings = research_data.get("headings", [])
        competitor_headings_str = "\n".join(headings[:15])

        messages = [
            {
                "role": "system",
                "content": (
                    get_persian_anchor(topic)
                    + " "
                    "خروجی تو باید منحصراً یک شیء JSON معتبر باشد که کلیدها و مقادیر آن داخل double quote قرار دارند. "
                    "هیچ متن، توضیح یا دیتای اضافه‌ای خارج از ساختار JSON ننویس."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"موضوع مقاله: {topic}\n"
                    f"کلمه کلیدی اصلی: {keyword}\n\n"
                    f"تیترهای الهام‌بخش از رقبا:\n"
                    f"{competitor_headings_str}\n\n"
                    "یک نقشه راه (Outline) مهندسی شده، کاملاً منطقی و عاری از تخیلاتِ غیرعلمی برای این مقاله طراحی کن.\n"
                    "ساختار دقیق JSON خروجی باید به این شکل باشد:\n"
                    "{\n"
                    '  "h1": "عنوان اصلی و جذاب که حتماً شامل کلمه کلیدی باشد",\n'
                    '  "meta_description": "توضیح جذاب و کنجکاوی‌برانگیز بین ۱۵۰ تا ۱۶۰ کاراکتر فارسی",\n'
                    '  "sections": [\n'
                    "    {\n"
                    '      "h2": "عنوان بخش اصلی — جذاب، منحصربه‌فرد و منطبق بر واقعیت",\n'
                    '      "content_angle": "توضیح دو خطی برای نویسنده که دقیقاً چه دیتای علمی و مفیدی در این بخش باز شود",\n'
                    '      "h3_list": ["زیرعنوان مرتبط ۱", "زیرعنوان مرتبط ۲"],\n'
                    '      "key_points": ["نکته کلیدی و واقعی ۱", "نکته کلیدی ۲"]\n'
                    "    }\n"
                    "  ],\n"
                    '  "lsi_keywords": ["کلمه مرتبط صنعتی ۱", "کلمه مرتبط ۲", "کلمه مرتبط ۳", "کلمه مرتبط ۴", "کلمه مرتبط ۵"]\n'
                    "}\n\n"
                    "قوانین حیاتیِ نقشه:\n"
                    "- آرایه sections باید شامل ۵ تا ۷ بخش H2 باشد.\n"
                    "- تحت هیچ شرایطی تیترهای متناقض و غیرعلمی تولید نکن.\n"
                    "- تمام متون داخل JSON خالصِ فارسی باشند."
                ),
            },
        ]
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

        safe_history_footprint = distill_memory(previous_context)

        messages = [
            {
                "role": "system",
                "content": (
                    get_persian_anchor(keyword)
                    + " "
                    "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
                    "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» پرهیز کن."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"ماموریت تو نگارش متنِ کامل، فاخر و غنی منحصراً برای بخش با عنوان «{h2_title}» است.\n\n"
                    f"زاویه دید و هدایت محتوایی: {content_angle}\n"
                    f"زیرعنوان‌های خواسته شده: {h3_str}\n"
                    f"نکات کلیدی که باید باز شوند:\n{key_points_str}\n\n"
                    f"=== [ردپای موضوعاتِ گفته شده در بخش‌های قبل] ===\n"
                    f"({safe_history_footprint})\n"
                    "قانونِ پیوستگی: با نگاه به ردپای بالا، حرف‌های تکراری نزن و مستقیماً وارد دیتای اختصاصیِ همین تیتر شو.\n"
                    f"=================================================\n\n"
                    f"کلمه کلیدی هدف (یک بار حل شده در متن): {keyword}\n"
                    f"کلمات LSI مرتبط: {lsi_str}\n\n"
                    "قوانینِ حیاتیِ نگارش:\n"
                    "۱. ممنوعیت حشو و بدیهیات: مستقیماً وارد دیتای اختصاصی، تکنیک یا چراییِ علمیِ آن موضوع شو.\n"
                    "۲. خلوصِ واژگانی: اصطلاحاتِ تخصصیِ یک صنعت را به صنعتِ دیگر نچسبان.\n"
                    "۳. تنوعِ طولِ جملات: ریتمِ متن را با ترکیبِ جملات کوتاه و بلند، گوش‌نواز کن.\n"
                    "۴. ممنوعیتِ کال‌تو‌اکشنِ تنبلانه: در انتهای پاراگراف‌ها عباراتی مثل «برای کسب اطلاعات بیشتر به صفحه مربوطه مراجعه کنید» ننویس.\n"
                    "۵. ساختار HTML: بدنه را داخل تگ <p> بگذار. خروجی فقط کدهای HTML بدنه باشد."
                ),
            },
        ]

        raw = await self.llm.generate(messages)
        return sanitize_html_for_tiptap(raw)