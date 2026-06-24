import json
import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


def get_system_anchor(domain_context: str) -> str:
    return f"""تو یک پژوهشگرِ برجسته، متخصصِ کنترلِ کیفیت و سردبیرِ تراز اولِ وبِ فارسی در حوزه‌ی «{domain_context}» هستی.
معماریِ کلامِ تو مبتنی بر «اصالتِ فیزیکیِ اشیاء، منطقِ سفت‌وسختِ علمی، و نثری پیوسته» است.

قوانینِ بنیادینِ پردازشِ ذهنیِ تو:
۱. قانونِ فیزیکِ اشیاء (Strict Material Reality): خواصِ مواد را تحریف نکن! (مثلاً پلاستیک 'زنگ نمی‌زند'، بلکه می‌پوسد یا می‌شکند؛ فولادِ ضدزنگ 'استریل نمی‌کند'، بلکه در برابرِ اکسید شدن مقاوم است). حقایقِ متالورژی و شیمیایی را دقیق بنویس.
۲. طردِ تخیلاتِ سایبرپانک: ابزارهایِ مکانیکیِ ساده (مثل ناخن‌گیر یا چکش) دارایِ 'سیستم‌هایِ پیشرفته‌یِ الکترونیکی یا استریلِ داخلی' نیستند! آلودگی‌زداییِ یک ابزار، 'عملی' است که کاربر با الکل یا حرارت روی آن انجام می‌دهد، نه آپشنی در داخلِ خودِ دستگاه.
۳. ممنوعیتِ تضادِ معنایی: عباراتی مثل «برای جلوگیری از آلودگی‌زدایی» یک باگِ خنده‌دارِ نگارشی است؛ منظورِ تو «برای پیشگیری از انتقالِ آلودگی» یا «جهتِ سهولت در گندزدایی» است. مفاهیم را درست متصل کن.
۴. زبانِ خالص: کلِ متن باید به زبانِ فارسیِ معیار و زنده باشد."""


_ALIEN_BYTE_FILTER = re.compile(
    r"[\u0900-\u097F"  # هندی / سانسکریت
    r"\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF"  # کانجی / چینی / ژاپنی -> مهارِ «详»
    r"\u0E00-\u0E7F"  # تایلندی
    r"\u0400-\u04FF\u0500-\u052F"  # سیریلیک
    r"ạảăắằẳẵặâấầẩẫậẹẻẽêềếểễệỉịọỏôốồổỗộơớờởỡợụủưứừửữựỵỷỹĐđ"  # ویتنامی
    r"]+"
)


def pure_tree_walker_sanitizer(raw_html_output: str) -> str:
    if not raw_html_output:
        return ""

    cleaned = re.sub(
        r"<think>.*?</think>", "", raw_html_output, flags=re.DOTALL | re.IGNORECASE
    )
    cleaned = re.sub(r"\x60{3}html|\x60{3}", "", cleaned, flags=re.IGNORECASE)

    # <--- بازگشتِ شکوهمندانه‌ی جلادِ بایت‌ها (حلقه‌ی گمشده‌ی جراحیِ ۱۷)
    cleaned = _ALIEN_BYTE_FILTER.sub("", cleaned)

    cliches = [
        r"\bدر نتیجه،\b",
        r"\bبه طور کلی،\b",
        r"\bبنابراین،\b",
        r"\bهمان‌طور که گفته شد،\b",
        r"\bهمان‌گونه که می‌دانید،\b",
        r"\btherefore\b",
        r"\bconclusion\b",
        r"\bsummary\b",
        r"\bبه طور详یعی\b",  # شکارچیِ اختصاصیِ سوتیِ اخیر
    ]
    for cliche in cliches:
        cleaned = re.sub(cliche, "", cleaned, flags=re.IGNORECASE)

    soup = BeautifulSoup(cleaned, "html.parser")
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

    final_str = str(soup)
    final_str = re.sub(r" {2,}", " ", final_str)
    final_str = re.sub(r"\n{3,}", "\n\n", final_str)
    return final_str.strip()


def extract_safe_context(raw_html_history: str) -> str:
    if not raw_html_history or not raw_html_history.strip():
        return "بدنه‌ی مقاله هنوز آغاز نشده است."

    soup = BeautifulSoup(raw_html_history, "html.parser")
    written_headers = [h.get_text().strip() for h in soup.find_all(["h2", "h3"])]

    if not written_headers:
        return "مقدماتِ کلان نگارش یافته است."

    return f"تیترهای بسط داده شده تا این لحظه: ({' | '.join(written_headers[-4:])})"


class SEOGenerator:

    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def generate_outline(
        self, topic: str, keyword: str, research_data: dict[str, Any]
    ) -> dict[str, Any]:
        headings = research_data.get("headings", [])
        competitors_tree = "\n".join(headings[:12])

        sys_anchor = (
            f"تو یک معمارِ محتوا و سردبیرِ دانشنامه در حوزه‌ی «{topic}» هستی. "
            "وظیفه‌ی تو طراحیِ یک نقشه‌ی محتواییِ (Outline) کاملاً تخصصی، مستند و منطقی است. "
            "خروجی منحصراً یک شیء JSON معتبر باشد."
        )

        user_request = (
            f"موضوع کلان: {topic}\n"
            f"کلمه کلیدیِ هدف: {keyword}\n\n"
            f"ساختارِ تیترهای برترِ وب در این حوزه:\n{competitors_tree}\n\n"
            "یک نقشه‌ی JSON دقیق با این معماری برگردان:\n"
            "{\n"
            '  "h1": "عنوان جذاب حاوی کلمه کلیدی",\n'
            '  "meta_description": "توضیح متا بین ۱۵۰ تا ۱۶۰ کاراکتر",\n'
            '  "domain_glossary": {\n'
            '    "اصطلاح_تخصصی_انگلیسی_۱": "معادل_دقیق،_رایج_و_استاندارد_فارسی"،\n'
            '    "اصطلاح_انگلیسی_۲": "معادل_فارسی_۲"\n'
            "  },\n"
            '  "sections": [\n'
            "    {\n"
            '      "h2": "عنوان بخش اصلی"،\n'
            '      "core_thesis": "یک پاراگرافِ ۲ خطیِ پیوسته، منطقی و کاملاً علمی که در آن تمامِ حقایقِ فیزیکی، عملکردی و مشخصاتِ این تیتر به صورتِ یک متنِ یکپارچه روایت شده است"،\n'
            '      "h3_list": ["زیرتیتر مرتبط ۱", "زیرتیتر مرتبط ۲"]\n'
            "    }\n"
            "  ],\n"
            '  "lsi_keywords": ["کلمه هم‌خانواده ۱", "کلمه ۲", "کلمه ۳", "کلمه ۴", "کلمه ۵"]\n'
            "}\n\n"
            "قوانینِ حیاتیِ اسکیما:\n"
            "- بخش sections شامل ۵ تا ۷ بخش H2 باشد.\n"
            "- در فیلد core_thesis 절대اً از بولت‌پوینت استفاده نکن؛ فقط یک پاراگرافِ متنیِ خالص بنویس.\n"
            "- بخش domain_glossary شاملِ حداقل ۴ اصطلاحِ کلیدیِ این حوزه باشد."
        )

        messages = [
            {"role": "system", "content": sys_anchor},
            {"role": "user", "content": user_request},
        ]

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
        grounding_source_facts: str = "",
        previous_context: str = "",
    ) -> str:
        h3_str = "، ".join(h3_list) if h3_list else "بدون زیرعنوان H3"
        lsi_str = "، ".join(lsi_keywords[:6])
        glossary_str = (
            json.dumps(domain_glossary, ensure_ascii=False)
            if domain_glossary
            else "واژه‌نامه‌ی عمومی"
        )

        safe_history_report = extract_safe_context(previous_context)

        # تزریقِ فکت‌های واقعیِ سرچِ گوگل به مغزِ نویسنده
        facts_block = ""
        if grounding_source_facts:
            facts_block = (
                "\n\n=== [مواد خامِ علمیِ استخراج شده از جستجوی زنده گوگل] ===\n"
                f"{grounding_source_facts}\n"
                "=======================================================\n"
                "قانونِ استناد (Grounding): در بسط دادنِ متن، منحصراً به فکت‌هایِ بالا تکیه کن و از تخیلاتِ غیرمنطقی بپرهیز.\n"
            )

        sys_anchor = (
            get_system_anchor(keyword)
            + " "
            "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
            "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» پرهیز کن."
        )

        user_request = (
            f"بخشِ تحتِ نگارش: «{h2_title}»\n"
            f"زیرعنوان‌ها: {h3_str}\n"
            f"تزِ محتواییِ این بخش:\n«{core_thesis}»\n"
            f"{facts_block}\n"
            f"واژه‌نامه‌ی اختصاصیِ صنف:\n{glossary_str}\n\n"
            f"وضعیتِ پیشرفتِ مقاله:\n[{safe_history_report}]\n"
            "با نگاه به گزارشِ بالا، مطالبِ گفته شده در تیترهای قبل را مطلقاً تکرار نکن.\n\n"
            f"کلمه کلیدیِ هدف: {keyword} (یک بار در متن حل شود)\n"
            f"کلماتِ LSI: {lsi_str}\n\n"
            "قوانینِ حیاتی نگارش:\n"
            "۱. قفلِ ضد لکنت (Anti-Loop): تکرارِ یک جمله در انتهای دو پاراگرافِ متوالی، ممنوع است!\n"
            "۲. پرهیز از تکرارِ کلماتِ کلیشه‌ای: کلماتی مثل 'بهداشتی و کارآمد' را مثل طوطی در هر خط تکرار نکن؛ از مترادف‌های پویا استفاده کن.\n"
            "۳. ممنوعیتِ ارجاعِ کلیشه‌ای: عباراتی مثل «برای کسب اطلاعات بیشتر به صفحه‌ی مربوطه مراجعه کنید» ننویس.\n"
            "۴. فرمت خروجی: متن بدنه داخل تگ <p>. حداکثر ۳ خط در هر پاراگراف. خروجی فقط کدهای HTML بدنه باشد."
        )

        messages = [
            {"role": "system", "content": sys_anchor},
            {"role": "user", "content": user_request},
        ]

        raw_html = await self.llm.generate(messages)
        return pure_tree_walker_sanitizer(raw_html)