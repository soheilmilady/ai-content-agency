import re

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
    r'[^\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF'  # Unicode فارسی/عربی
    r'\u06F0-\u06F9'        # اعداد فارسی
    r'0-9'                  # اعداد لاتین
    r'\s'                   # فاصله و newline
    r'،؟!.,:;\-\(\)\[\]«»'  # نقطه‌گذاری
    r'<>/="\'`'             # HTML tags
    r']+'
)

# کلمات غیرفارسی شناخته‌شده که مدل‌ها گاهی تولید می‌کنند
_KNOWN_FOREIGN = re.compile(
    r'\b(ayrıca|también|aussi|льод|вкус|industria|melhor|популяр|'
    r'필요|また|também|además|également|inoltre|außerdem|также|'
    r'furthermore|however|therefore|moreover)\b',
    re.IGNORECASE
)


def clean_persian_text(text: str) -> str:
    """کلمات و کاراکترهای غیرفارسی را از متن HTML حذف می‌کند."""
    # ابتدا کلمات غیرفارسی شناخته‌شده را حذف کن
    text = _KNOWN_FOREIGN.sub('', text)

    # کاراکترهای غیرمجاز خارج از HTML tags را حذف کن
    # HTML tags رو جدا کن و محتوا رو پاک کن
    parts = re.split(r'(<[^>]+>)', text)
    cleaned_parts = []
    for part in parts:
        if part.startswith('<'):
            # HTML tag — دست نزن
            cleaned_parts.append(part)
        else:
            # متن — کاراکترهای غیرمجاز رو حذف کن
            cleaned_parts.append(_ALLOWED.sub(' ', part))

    result = ''.join(cleaned_parts)
    # فاصله‌های اضافه رو پاک کن
    result = re.sub(r' {2,}', ' ', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


class SEOGenerator:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(
        self, topic: str, keyword: str, research_data: dict
    ) -> dict:
        headings = research_data.get("headings", [])
        messages = [
            {
                "role": "system",
                "content": (
                    PERSIAN_SYSTEM + " "
                    "تو یک متخصص سئو هستی. "
                    "فقط JSON معتبر با کلیدها و مقادیر داخل double quote برگردان. "
                    "هیچ توضیح، مقدمه یا متن اضافه خارج از JSON ننویس."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"موضوع: {topic}\n"
                    f"کلمه کلیدی اصلی: {keyword}\n"
                    f"تیترهای رقبا برای الهام (نه کپی): {headings}\n\n"
                    "یک ساختار مقاله کامل با این فرمت JSON دقیق بساز:\n"
                    "{\n"
                    '  "h1": "عنوان اصلی که حتماً شامل کلمه کلیدی باشد",\n'
                    '  "meta_description": "توضیح جذاب ۱۵۰ تا ۱۶۰ کاراکتر فارسی",\n'
                    '  "sections": [\n'
                    '    {\n'
                    '      "h2": "عنوان بخش اصلی — منحصربه‌فرد و کاملاً متفاوت از H3",\n'
                    '      "h3_list": ["زیرعنوان متفاوت ۱", "زیرعنوان متفاوت ۲"],\n'
                    '      "key_points": ["نکته دقیق ۱", "نکته دقیق ۲", "نکته دقیق ۳"]\n'
                    '    }\n'
                    "  ],\n"
                    '  "lsi_keywords": ["کلمه مرتبط ۱", "کلمه مرتبط ۲", "کلمه مرتبط ۳"]\n'
                    "}\n\n"
                    "قوانین مهم:\n"
                    "- حداقل ۵ بخش H2 بساز\n"
                    "- عنوان H2 و H3های هر بخش باید کاملاً متفاوت از هم باشند\n"
                    "- هیچ دو بخشی عنوان یکسان یا مشابه نداشته باشند\n"
                    "- key_points باید اطلاعات واقعی و مفید باشند، نه کلی‌گویی\n"
                    "- همه متون داخل JSON فارسی باشند"
                ),
            },
        ]
        raw = await self.llm.generate(messages, json_mode=True)
        return parse_json_response(raw)

    async def draft_section(
        self,
        h2_title: str,
        key_points: list[str],
        keyword: str,
        lsi_keywords: list[str],
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    PERSIAN_SYSTEM + " "
                    "تو یک نویسنده محتوای حرفه‌ای فارسی هستی. "
                    "متن روان، طبیعی، اطلاعاتی و کاملاً اصیل بنویس. "
                    "هرگز عنوان H2 را داخل متن تکرار نکن. "
                    "از کلی‌گویی و جملات تکراری بپرهیز — هر جمله اطلاعات جدیدی بدهد."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"برای بخش با عنوان «{h2_title}» متن کامل و اطلاعاتی بنویس.\n\n"
                    f"نکات محتوایی که باید پوشش داده شوند:\n"
                    + "\n".join(f"- {p}" for p in key_points) + "\n\n"
                    f"کلمه کلیدی اصلی (یک بار به طور طبیعی استفاده کن): {keyword}\n"
                    f"کلمات مرتبط (طبیعی و پراکنده استفاده کن): {', '.join(lsi_keywords)}\n\n"
                    "قوانین نگارش:\n"
                    "- طول کل متن: ۱۵۰ تا ۲۵۰ کلمه فارسی خالص\n"
                    "- هر جمله زیر ۲۵ کلمه باشد\n"
                    "- هر پاراگراف حداکثر ۳ خط باشد\n"
                    "- عنوان بخش را در ابتدا تکرار نکن\n"
                    "- اگر زیرعنوان داری از <h3> استفاده کن، برای پاراگراف از <p>\n"
                    "- هیچ کلمه غیرفارسی (به‌جز اصطلاحات فنی تخصصی) ننویس\n"
                    "- هر جمله باید اطلاعات مفید و جدید داشته باشد\n\n"
                    "فقط HTML خروجی بده، بدون توضیح اضافه."
                ),
            },
        ]
        raw = await self.llm.generate(messages)
        return clean_persian_text(raw)