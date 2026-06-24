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

# کاراکترهای مجاز: فارسی، اعداد، نقطه‌گذاری، فاصله، و حروف انگلیسی برای اصطلاحات فنی (مثل PE100 یا PVC)
_ALLOWED = re.compile(
    r"[^\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF"  # Unicode فارسی/عربی
    r"\u06F0-\u06F9"  # اعداد فارسی
    r"0-9"  # اعداد لاتین
    r"a-zA-Z"  # <--- ناجیِ اصطلاحات تخصصی: حروف انگلیسی مجاز شدند!
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
    text = _KNOWN_FOREIGN.sub("", text)

    parts = re.split(r"(<[^>]+>)", text)
    cleaned_parts = []
    for part in parts:
        if part.startswith("<"):
            cleaned_parts.append(part)
        else:
            cleaned_parts.append(_ALLOWED.sub(" ", part))

    result = "".join(cleaned_parts)
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
                    f"تیترهایی که رقبای برتر گوگل در این موضوع نوشته‌اند جهت الهام:\n"
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

        memory_block = ""
        if previous_context:
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
                    "تو یک ژورنالیست صنعتی، نویسندهٔ پختهٔ بازار خاورمیانه و سردبیر محتوای وب‌سایت هستی. "
                    "لحن تو توصیفی، تحلیلی، غنی و کاملاً انسانی است. "
                    "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
                    "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» یا «در این بخش» پرهیز کن."
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
                    "قوانینِ حیاتیِ کالیبراسیونِ متن (بسیار مهم):\n"
                    "۱. تنوع ضمیر (Anti-Stuffing): به جای تکرارِ رباتیک و آزاردهندهٔ کلمهٔ «لوله پلی‌اتیلن» در شروعِ تمام جملات، از تنوعِ بیانی (مانند: این محصول، پایپ‌های پلیمری، نمونه‌های صادراتی، این شاه‌لوله‌ها) استفاده کن.\n"
                    "۲. اعتدال در کلمات ربط: استفاده از کلمات متصل‌کننده (مضاف بر این، با این اوصاف، از سوی دیگر) مجاز است اما در کلِ این بخش، نهایتاً «فقط یک بار» از این کلمات استفاده کن! متن را شبیه انشای تصنعی نکن.\n"
                    "۳. واقع‌گراییِ بازارِ خاورمیانه (Grounding): وقتی دربارهٔ صادراتِ صنعتی از مبدأ ایران می‌نویسی، فکت‌های واقعی را لحاظ کن. بازارهای هدفِ لولهٔ ایران عمدتاً کشورهای همسایه (عراق، افغانستان، ترکمنستان، ارمنستان، پاکستان، عمان) و کشورهای آفریقایی هستند. تحت هیچ شرایطی نام کشورهای اروپای غربی (مثل آلمان یا فرانسه) یا آمریکا را به عنوان خریدارِ کالای تحت تحریمِ ایران ننویس!\n"
                    "۴. اصطلاحات فنی: استفاده از کلمات انگلیسیِ تخصصیِ صنعت (مانند PE80, PE100, HDPE, SDR, PN) در متن کاملاً مجاز و نشان‌دهندهٔ تخصصِ نویسنده است.\n"
                    "۵. ممنوعیتِ ارجاعِ تنبلانه (No Lazy CTAs): تحت هیچ شرایطی در انتهای پاراگراف‌ها عبارات کلیشه‌ای مثل «برای کسب اطلاعات بیشتر به صفحه مربوطه مراجعه کنید» ننویس.\n"
                    "۶. ساختار بصری: بدنه را داخل تگ <p> قرار بده. حداکثر ۳ تا ۴ خط در هر پاراگراف. خروجی فقط کدهای HTML بدنه باشد."
                ),
            },
        ]

        raw = await self.llm.generate(messages)
        return clean_persian_text(raw)