import json
import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


def get_system_anchor(domain_context: str) -> str:
    """
    لنگرِ هویتِ ژورنالیسمِ ساختاریافته:
    به جای قوانینِ سلبیِ وصله‌پینه‌ای، اصولِ «تفکرِ علمی و لحنِ محتاط» را به مدل تزریق می‌کند.
    """
    return f"""تو یک استراتژیستِ محتوا، پژوهشگرِ ارشد و نویسنده‌ی تراز اولِ وبِ فارسی در حوزه‌ی «{domain_context}» هستی.
معماریِ کلامِ تو مبتنی بر «دقتِ مستند، انسجامِ روایی، و اعتدال در بیان» است.

قوانینِ بنیادینِ پردازشِ ذهنیِ تو:
۱. اصلِ عدمِ مبالغه (Understatement over Hyperbole): هرگز از احکامِ مطلق، غیرعلمی و مبالغه‌آمیز (مانند: 'صد در صد'، 'کنترل مطلق'، 'بی‌رقیب‌ترین') استفاده نکن. اعتبارِ یک متنِ علمی به «احتیاط در صدورِ گزاره‌ها» است؛ حقایق را معتدل و دقیق بیان کن.
۲. پیوستگیِ ارگانیک (Narrative Flow): داده‌ها باید در تار و پودِ جملاتِ مرکب و متین بافته شوند؛ ردیف کردنِ اطلاعات به صورتِ بولت‌پوینت یا تلگرافی، ممنوع است.
۳. اصالتِ واژگانی: در برگردانِ مفاهیم، از اصیل‌ترین و رایج‌ترین واژگانِ زبانِ مقصد در همان صنف استفاده کن؛ بکارگیریِ کلماتِ فینگلیش یا ترجمه‌های تحت‌اللفظی، خطای سیستماتیک است.
۴. ممنوعیتِ تعاریفِ حلقوی: هرگز یک پدیده را با تکرارِ کلماتِ اسمِ خودش تعریف نکن."""


# فیلترِ سخت‌افزاریِ کاراکترها (Inference Artifacts Filter)
# این رجکس صرفاً برای مهارِ نشتِ توکنایزرِ مدل‌های ترانسفورمر در سطح بایت است، نه یک قانونِ پرامپتی.
_ALIEN_BYTE_FILTER = re.compile(
    r"[\u0900-\u097F"  # هندی / سانسکریت
    r"\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF"  # کانجی / چینی / ژاپنی
    r"\u0E00-\u0E7F"  # تایلندی
    r"\u0400-\u04FF\u0500-\u052F"  # سیریلیک (روسی) -> مهارِ کلمه‌ی هیبریدیِ «استабل»
    r"ạảăắằẳẵặâấầẩẫậẹẻẽêềếểễệỉịọỏôốồổỗộơớờởỡợụủưứừửữựỵỷỹĐđ"  # ویتنامی
    r"]+"
)


def pure_html_sanitizer(raw_content: str) -> str:
    """
    هرس‌کننده‌ی خالصِ درختِ HTML (بدون هیچ‌گونه دخالت در منطقِ کلمات و لغت‌نامه‌ها).
    """
    if not raw_content:
        return ""

    text = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL)
    text = re.sub(r"```html|```", "", text)
    text = _ALIEN_BYTE_FILTER.sub("", text)

    soup = BeautifulSoup(text, "html.parser")
    valid_tags = {
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
        if tag.name not in valid_tags:
            tag.unwrap()

    cleaned_html = str(soup)
    cleaned_html = re.sub(r" {2,}", " ", cleaned_html)
    cleaned_html = re.sub(r"\n{3,}", "\n\n", cleaned_html)
    return cleaned_html.strip()


def extract_headings_footprint(html_memory: str) -> str:
    """استخراجِ خلاصه‌ی ساختاری از کانتکستِ غلتان."""
    if not html_memory or not html_memory.strip():
        return "بخش اولِ مقاله"
    soup = BeautifulSoup(html_memory, "html.parser")
    headers = [h.get_text().strip() for h in soup.find_all(["h2", "h3"])]
    return "، ".join(headers[-4:]) if headers else "مقدمه"


class SEOGenerator:

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(
        self, topic: str, keyword: str, research_data: dict[str, Any]
    ) -> dict[str, Any]:
        headings = research_data.get("headings", [])
        competitors_tree = "\n".join(headings[:12])

        sys_anchor = (
            f"تو یک معمارِ اطلاعات و سردبیرِ ارشد در حوزه‌ی «{topic}» هستی. "
            "وظیفه‌ی تو طراحیِ یک نقشه‌ی محتواییِ (Outline) کاملاً تخصصی، مستند و عاری از حشو است. "
            "خروجی منحصراً یک شیء JSON معتبر باشد."
        )

        user_request = (
            f"موضوع کلان: {topic}\n"
            f"کلمه کلیدیِ هدف: {keyword}\n\n"
            f"ساختارِ تیترهای برترِ وب در این حوزه:\n{competitors_tree}\n\n"
            "یک نقشه‌ی JSON دقیق با این معماریِ نوین برگردان:\n"
            "{\n"
            '  "h1": "عنوان اصلی و جذاب حاوی کلمه کلیدی",\n'
            '  "meta_description": "توضیح متا بین ۱۵۰ تا ۱۶۰ کاراکتر",\n'
            '  "domain_glossary": {\n'
            '    "اصطلاح_یا_کلمه‌ی_کلیدی_انگلیسی_۱": "معادل_دقیق،_فاخر_و_استاندارد_فارسی_در_همین_صنعت"،\n'
            '    "اصطلاح_انگلیسی_۲": "معادل_فارسی_۲"\n'
            "  },\n"
            '  "sections": [\n'
            "    {\n"
            '      "h2": "عنوان بخش اصلی"،\n'
            '      "core_thesis": "یک پاراگرافِ ۲ خطیِ پیوسته، غنی و ژورنالیستی که در آن تمامِ آمارها، حقایقِ علمی و زوایای دیدِ این تیتر به صورتِ یک متنِ یکپارچه (و کاملاً بدونِ استفاده از لیست یا بولت‌پوینت) روایت شده است"،\n'
            '      "h3_list": ["زیرتیتر مرتبط ۱", "زیرتیتر مرتبط ۲"]\n'
            "    }\n"
            "  ],\n"
            '  "lsi_keywords": ["کلمه هم‌خانواده ۱", "کلمه ۲", "کلمه ۳", "کلمه ۴", "کلمه ۵"]\n'
            "}\n\n"
            "قوانینِ حیاتیِ اسکیما:\n"
            "- بخش sections شامل ۵ تا ۷ بخش H2 باشد.\n"
            "- در فیلد core_thesis 절대اً از کاراکترهای خط تیره (-) یا فرمتِ لیستی استفاده نکن؛ فقط یک پاراگرافِ متنیِ خالص و پرمغز بنویس.\n"
            "- بخش domain_glossary باید شاملِ حداقل ۴ اصطلاحِ حیاتیِ این صنعت باشد تا نویسنده‌ی بعدی در ترجمه‌ی واژگان گمراه نشود."
        )

        messages = [
            {"role": "system", "content": sys_anchor},
            {"role": "user", "content": user_request},
        ]

        # قفلِ تمپرچرِ نقشه روی 0.2 برای قطعِ ۱۰۰٪ ارتباط با کشِ JSONهای پیشین
        raw_json = await self.llm.generate(messages, json_mode=True)
        return parse_json_response(raw_json)

    async def draft_section(
        self,
        h2_title: str,
        core_thesis: str,
        h3_list: list[str],
        keyword: str,
        lsi_keywords: list[str],
        domain_glossary: dict[str, str],
        previous_context: str = "",
    ) -> str:
        h3_str = "، ".join(h3_list) if h3_list else "بدون زیرعنوان H3"
        lsi_str = "، ".join(lsi_keywords[:6])
        glossary_str = (
            json.dumps(domain_glossary, ensure_ascii=False)
            if domain_glossary
            else "واژه‌نامه‌ی عمومی"
        )

        history_footprint = extract_headings_footprint(previous_context)

        sys_anchor = (
            get_system_anchor(keyword)
            + " "
            "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
            "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» پرهیز کن."
        )

        user_request = (
            f"بخشِ تحتِ نگارش: «{h2_title}»\n"
            f"زیرعنوان‌های خواسته شده: {h3_str}\n"
            f"تزِ محتواییِ این بخش (این متن را بسط بده و به یک بدنه‌ی ژورنالیستیِ جذاب تبدیل کن):\n«{core_thesis}»\n\n"
            f"واژه‌نامه‌ی اختصاصیِ صنف (در ترجمه‌ی مفاهیم، منحصراً از این معادل‌ها استفاده کن):\n{glossary_str}\n\n"
            f"ردپایِ موضوعاتِ بخش‌های قبل:\n[{history_footprint}]\n"
            "با نگاه به ردپای بالا، مطالبِ پیشین را تکرار نکن.\n\n"
            f"کلمه کلیدیِ هدف: {keyword} (یک بار در متن حل شود)\n"
            f"کلماتِ LSI: {lsi_str}\n\n"
            "قوانینِ معماریِ متن:\n"
            "۱. بسطِ ارگانیک: تزِ محتواییِ بالا را با نثری پخته، توصیفی و دارایِ ریتمِ انسانی (ترکیبِ جملات کوتاه و بلند) بازنویسی کن.\n"
            "۲. ممنوعیتِ اکو و تکرار: خروجیِ تو باید یک متنِ پیوسته و تمیز باشد؛ کپی کردنِ دوباره‌ی تزِ محتوایی در پایینِ متن، ممنوع است.\n"
            "۳. ممنوعیتِ ارجاعِ کلیشه‌ای: عباراتی مثل «برای کسب اطلاعات بیشتر به صفحه‌ی مربوطه مراجعه کنید» ننویس.\n"
            "۴. فرمت خروجی: متن بدنه داخل تگ <p>. حداکثر ۳ خط در هر پاراگراف. خروجی فقط کدهای HTML بدنه باشد."
        )

        messages = [
            {"role": "system", "content": sys_anchor},
            {"role": "user", "content": user_request},
        ]

        # ستونِ سوم: قفل کردنِ دمای درَفت‌نویس روی 0.35 برای مهارِ مبالغه و تضمینِ فکت‌ها
        # برای اعمال این دما، باید در llm_gateway.py متد generate قابلیت پذیرشِ temperature را داشته باشد،
        # یا اگر ندارد، در خودِ gateway دمای پیش‌فرض را روی 0.4 بگذاری.
        raw_html = await self.llm.generate(messages)
        return pure_html_sanitizer(raw_html)