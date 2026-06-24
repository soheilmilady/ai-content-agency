import re
from typing import Any

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

PERSIAN_SYSTEM = (
    "تمام خروجی را فقط و فقط به زبان فارسی روان و رسمی بنویس. "
    "از هیچ کلمه‌ای به زبان ترکی، روسی، عربی، اسپانیایی، پرتغالی، کره‌ای، ژاپنی "
    "یا هر زبان دیگری به‌جز فارسی استفاده نکن. "
    "اصطلاحات فنی رایج مانند کلدبرو، اسپرسو، فرنچ‌پرس، ایروپرس قابل قبول هستند. "
    "هرگز از این کلمات استفاده نکن: ayrıca، también، aussi، льود، вкус، industria، "
    "melhor، популяр،필요 یا هر کلمه مشابه غیرفارسی."
)

# کاراکترهای مجاز: فارسی، اعداد فارسی/عربی، نقطه‌گذاری فارسی، فاصله، خط تیره
_ALLOWED = re.compile(
    r"[^\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF"  # Unicode فارسی/عربی
    r"\u06F0-\u06F9"  # اعداد فارسی
    r"0-9"  # اعداد لاتین
    r"\s"  # فاصله و newline
    r"،؟!.,:;\-\(\)\[\]«»"  # نقطه‌گذاری
    r'<>/="\'`'  # HTML tags
    r"]+"
)

# کلمات غیرفارسی شناخته‌شده که مدل‌ها گاهی تولید می‌کنند
_KNOWN_FOREIGN = re.compile(
    r"\b(ayrıca|también|aussi|льод|вкус|industria|melhor|популяр|"
    r"필요|また|também|además|également|inoltre|außerdem|также|"
    r"furthermore|however|therefore|moreover)\b",
    re.IGNORECASE,
)


def clean_persian_text(text: str) -> str:
    """کلمات و کاراکترهای غیرفارسی را از متن HTML حذف می‌کند."""
    # ابتدا کلمات غیرفارسی شناخته‌شده را حذف کن
    text = _KNOWN_FOREIGN.sub("", text)

    # کاراکترهای غیرمجاز خارج از HTML tags را حذف کن
    # HTML tags رو جدا کن و محتوا رو پاک کن
    parts = re.split(r"(<[^>]+>)", text)
    cleaned_parts = []
    for part in parts:
        if part.startswith("<"):
            # HTML tag — دست نزن
            cleaned_parts.append(part)
        else:
            # متن — کاراکترهای غیرمجاز رو حذف کن
            cleaned_parts.append(_ALLOWED.sub(" ", part))

    result = "".join(cleaned_parts)
    # فاصله‌های اضافه رو پاک کن
    result = re.sub(r" {2,}", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


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
                    "تو یک استراتژیست ارشد سئو و سردبیر محتوای وب‌سایت هستی. "
                    "خروجی تو باید منحصراً یک شیء JSON معتبر باشد که کلیدها و مقادیر آن داخل double quote قرار دارند. "
                    "هیچ متن، توضیح یا دیتای اضافه‌ای خارج از ساختار JSON ننویس."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"موضوع مقاله: {topic}\n"
                    f"کلمه کلیدی اصلی: {keyword}\n\n"
                    f"تیترهایی که رقبای برتر گوگل در این موضوع نوشته‌اند جهت الهام (نه کپی خالص):\n"
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
                    "- فیلد content_angle و key_points باید حاوی اطلاعات و جهت‌دهیِ واقعی باشند، نه کلی‌گویی.\n"
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
        key_points_str = "\n".join(f"- {p}" for p in key_points) if key_points else "تمرکز روی زاویه دید"
        lsi_str = "، ".join(lsi_keywords[:6])

        # آماده‌سازی کانتکست غلتان برای جلوگیری از تکرار حرف‌های قبلی
        memory_block = ""
        if previous_context:
            # ارسال ۲۰۰۰ کاراکتر آخر از محتوای تولید شده تا این لحظه
            memory_slice = previous_context[-2000:]
            memory_block = (
                "\n\n=== [حافظه مقاله تا این لحظه] ===\n"
                "بخش‌های قبلی مقاله به این صورت نگارش یافته‌اند:\n"
                f'"""{memory_slice}"""\n'
                "=====================================\n\n"
                "قانون تداوم (Continuity): با توجه به حافظه بالا، به هیچ وجه مطالب، تعاریف اولیه و جملات بخش‌های قبل را تکرار نکن! "
                "متن این بخش را طوری شروع کن که انگار ادامهٔ منطقی و جذابِ متنِ قبلی است."
            )

        messages = [
            {
                "role": "system",
                "content": (
                    PERSIAN_SYSTEM + " "
                    "تو یک ژورنالیست صنعتی و نویسنده محتوای ارشد وب‌سایت هستی. "
                    "لحن تو توصیفی، تحلیلی، بالغ، روان و کاملاً انسانی است. "
                    "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
                    "از کلی‌گویی، جملات مقطعِ کتاب درسی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» یا «در این بخش قصد داریم» به شدت پرهیز کن. "
                    "هر جمله باید حامل اطلاعات، آمار یا تحلیلی جدید و ارزشمند باشد."
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
                    f"کلمه کلیدی هدف (یک بار به طور کاملاً طبیعی و حل شده در متن استفاده کن): {keyword}\n"
                    f"کلمات LSI مرتبط (پراکنده و طبیعی در جملات به کار ببر): {lsi_str}\n\n"
                    "قوانین نگارش:\n"
                    "- طول خالص متن این بخش: ۱۸۰ تا ۲۸۰ کلمه فارسی.\n"
                    "- طول جملات متنوع باشد اما ترجیحاً جملات طولانی و خسته‌کننده ننویس (حداکثر ۲۵ کلمه).\n"
                    "- پاراگراف‌ها کوتاه و چشم‌نواز باشند (حداکثر ۳ تا ۴ خط).\n"
                    "- اگر در متن نیاز به تفکیک موضوعی بود، از تگ <h3> برای زیرعنوان‌ها و از تگ <ul>/<li> برای لیست‌ها استفاده کن.\n"
                    "- متن بدنه را حتماً داخل تگ <p> قرار بده.\n"
                    "- خروجی فقط و فقط کدهای HTML بدنه این بخش باشد. از نوشتن تگ‌های <html>، <body> یا خودِ تیتر <h2> خودداری کن."
                ),
            },
        ]

        raw = await self.llm.generate(messages)
        return clean_persian_text(raw)