import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

# تغییر لنگر از «فیلسوفِ باستانی» به «سردبیرِ مدرنِ وب فارسی»
PERSIAN_SYSTEM = (
    "تو یک سردبیرِ ارشد، ویراستارِ مسلط و ژورنالیستِ مدرنِ وب در رسانه‌های معتبری مانند «دیجی‌کالا مگ» یا وبلاگ‌های تخصصیِ لایف‌استایل هستی. "
    "نثر تو امروزی، تمیز، مینیمال، روان و کاملاً استاندارد است. "
    "از به کار بردنِ افعالِ وارونه (مانند: «چیست این قهوه»)، کلماتِ من‌درآوردی و هیبریدی (مانند: محببان، مادهشی، آبجکتور) و ادبیاتِ متکلفِ باستانی به شدت پرهیز کن. "
    "زبانِ خروجی باید ۱۰۰٪ فارسیِ اصیل و قابل فهم برای کاربرِ امروزیِ اینترنت باشد."
)

_ALIEN_SCRIPTS = re.compile(
    r"[\u0900-\u097F"
    r"\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF"
    r"\u0E00-\u0E7F"
    r"\u0400-\u04FF"
    r"ạảăắằẳẵặâấầẩẫậẹẻẽêềếểễệỉịọỏôốồổỗộơớờởỡợụủưứừửữựỵỷỹĐđ"
    r"]+"
)

_KNOWN_FOREIGN_WORDS = re.compile(
    r"\b(drinking|prepare|zwischen|cold brew|filter|also|however|moreover|furthermore|phổ biến|coffee|moka|pot|involvement|depending)\b",
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
                    PERSIAN_SYSTEM + " "
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
                    "یک نقشه راه (Outline) مهندسی شده، جذاب و جامع برای این مقاله طراحی کن که از محتوای رقبا غنی‌تر باشد.\n"
                    "ساختار دقیق JSON خروجی باید به این شکل باشد:\n"
                    "{\n"
                    '  "h1": "عنوان اصلی و جذاب که حتماً شامل کلمه کلیدی باشد",\n'
                    '  "meta_description": "توضیح جذاب و کنجکاوی‌برانگیز بین ۱۵۰ تا ۱۶۰ کاراکتر فارسی",\n'
                    '  "sections": [\n'
                    "    {\n"
                    '      "h2": "عنوان بخش اصلی — جذاب، منحصربه‌فرد و متفاوت از بقیه تیترها",\n'
                    '      "content_angle": "توضیح دو خطی برای نویسنده که دقیقاً چه زاویه دید و مفهومی در این بخش باز شود",\n'
                    '      "h3_list": ["زیرعنوان مرتبط ۱", "زیرعنوان مرتبط ۲"],\n'
                    '      "key_points": ["نکته کلیدی و دقیق ۱", "نکته کلیدی و دقیق ۲"]\n'
                    "    }\n"
                    "  ],\n"
                    '  "lsi_keywords": ["کلمه مرتبط صنعتی ۱", "کلمه مرتبط ۲", "کلمه مرتبط ۳", "کلمه مرتبط ۴", "کلمه مرتبط ۵"]\n'
                    "}\n\n"
                    "قوانین حیاتی:\n"
                    "- آرایه sections باید شامل حداقل ۵ تا ۷ بخش H2 باشد.\n"
                    "- عنوان H2 و H3های هر بخش باید کاملاً متفاوت از هم باشند و تکرار نشوند.\n"
                    "- فیلد content_angle و key_points باید حاوی اطلاعات واقعی باشند، نه کلی‌گویی.\n"
                    "- تمام متون داخل JSON باید به زبان فارسی خالص باشند."
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

        memory_block = ""
        if previous_context:
            memory_slice = previous_context[-2000:]
            memory_block = (
                "\n\n=== [حافظه مقاله تا این لحظه] ===\n"
                "بخش‌های قبلی مقاله به این صورت نگارش یافته‌اند:\n"
                f'"""{memory_slice}"""\n'
                "=====================================\n\n"
                "قانون تداوم (Continuity): با توجه به حافظه بالا، مطالب و تعاریفِ بخش‌های قبل را تکرار نکن! "
                "متن این بخش را طوری شروع کن که ادامهٔ طبیعیِ متنِ قبلی باشد."
            )

        messages = [
            {
                "role": "system",
                "content": (
                    PERSIAN_SYSTEM + " "
                    "تو یک نویسندهٔ باهوش، منطقی و مسلط به نگارشِ وب هستی. "
                    "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
                    "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «در این بخش می‌خواهیم» پرهیز کن."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"ماموریت تو نگارش متنِ کامل، غنی و اطلاعاتی منحصراً برای بخش با عنوان «{h2_title}» است.\n\n"
                    f"زاویه دید و هدایت محتوایی: {content_angle}\n"
                    f"زیرعنوان‌های خواسته شده: {h3_str}\n"
                    f"نکات کلیدی که باید در متن باز شوند:\n{key_points_str}\n"
                    f"{memory_block}\n"
                    f"کلمه کلیدی هدف (یک بار به طور طبیعی در متن استفاده کن): {keyword}\n"
                    f"کلمات LSI مرتبط (طبیعی در جملات به کار ببر): {lsi_str}\n\n"
                    "قوانینِ حیاتیِ عقل سلیم و منطق (Sanity & Logic Guard):\n"
                    "۱. تطابق با قوانین فیزیک: تحت هیچ شرایطی گزاره‌های متناقض و احمقانه ننویس! (مثلاً نوشتنِ «عصاره‌گیری سرد با استفاده از آب جوش» غیرممکن است). عصاره‌گیری سرد منحصراً با آب سرد یا هم‌دمای اتاق انجام می‌شود.\n"
                    "۲. شناختِ ماهیتِ مواد: «شیر» یک افزودنیِ لبنی و مایع است؛ به کار بردنِ کلمهٔ «آلیاژ» برای شیر یک خطای فاحشِ منطقی است (آلیاژ ترکیب فلزات است!). به جای کلمات عجیب مثل «آبجکتور» یا «مادهشی»، از معادل‌های استاندارد (مانند: پارچ شیشه‌ای، ظرف مخصوص، شیرین‌کننده، افزودنیِ طعم‌دار) استفاده کن.\n"
                    "۳. پرهیز از اغراق‌های فلسفی: قهوه یک نوشیدنی است؛ ننویس که قهوه «بر کیفیت و طعم زندگی تأثیر می‌گذارد»! تأثیرات را در جغرافیا و کانتکستِ خودش (انرژی‌بخشی، طعمِ ملایم، اسیدیتهٔ پایین) نگه دار.\n"
                    "۴. خلوص زبانی: کلمات انگلیسی مثل involvement یا Depending نباید وسط متنِ فارسی تایپ شوند.\n"
                    "۵. ساختار بصری: بدنه را حتماً داخل تگ <p> قرار بده. حداکثر ۳ تا ۴ خط در هر پاراگراف. خروجی فقط کدهای HTML بدنه باشد."
                ),
            },
        ]

        raw = await self.llm.generate(messages)
        return sanitize_html_for_tiptap(raw)