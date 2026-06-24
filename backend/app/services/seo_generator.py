import json
import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


def get_system_anchor(domain_context: str) -> str:
    """
    لنگرِ هویتِ دانشنامه‌ای:
    هوش مصنوعی را ملزم به 'راستی‌آزماییِ فکت‌ها' و 'پرهیز از تکرارِ ساختاری' می‌کند.
    """
    return f"""تو یک پژوهشگرِ برجسته‌ی تاریخ، مستندنگارِ علمی و سردبیرِ تراز اولِ وبِ فارسی در حوزه‌ی «{domain_context}» هستی.
معماریِ کلامِ تو مبتنی بر «اصالتِ فکت‌ها، نثرِ معیارِ دانشگاهی، و پیوستگیِ بدونِ حشو» است.

قوانینِ بنیادینِ نگارشِ تو:
۱. وسواسِ علمی و تاریخی (Strict Grounding): وقایع، مکان‌ها، خدایان و اسامیِ تاریخی را منحصراً بر اساسِ حقایقِ مسلمِ جهانی بنویس. (مثلاً خلقِ اسامیِ من‌درآوردی یا تلفیقِ اساطیرِ فرهنگ‌ها با یکدیگر، خطای فاجعه‌بار محسوب می‌شود). حقایق را بدونِ مبالغه و باصلابت روایت کن.
۲. طردِ کاملِ لکنت و تکرار (Zero-Echo Policy): تحت هیچ شرایطی، یک جمله، گزاره یا ترکیبِ واژگانی را در یک پاراگراف یا پاراگراف‌های بعدی تکرار نکن. هر پاراگراف باید حاملِ دیتایِ کاملاً تازه باشد؛ اگر مطلبِ جدیدی درباره‌ی یک تیتر نداری، پاراگراف را کوتاه تمام کن.
۳. پرهیز از جملاتِ کلیشه‌ایِ جمع‌بندی: در انتهای پاراگراف‌ها، جملاتِ بی‌ارزشی مثل «در نتیجه این قوم تأثیر زیادی گذاشتند» یا «به این ترتیب آنها موفق شدند» ننویس.
۴. زبانِ زنده و خالص: کلِ متن باید به زبانِ فارسیِ اصیل، باصلابت و بدونِ گرته‌برداری از ساختارهای انگلیسی یا عربیِ کهنه (مثل استفاده از کلمه‌ی 'طلبیدند' به جای 'طلب کنند') باشد."""


def pure_tree_walker_sanitizer(raw_html_output: str) -> str:
    """
    هرس‌کننده‌ی ایمنِ درختِ HTML:
    تگ‌های تفکرِ LLM را پاک می‌کند اما مطلقاً به کلمات، حروف و گرامرِ داخلِ متن دست نمی‌زند
    تا پدیده‌ی 'کلماتِ بخار شده' کاملاً ریشه‌کن شود.
    """
    if not raw_html_output:
        return ""

    # هرس کردنِ پوسته‌ی تفکرِ لاما در صورتِ نشت به خروجی
    cleaned = re.sub(
        r"<think>.*?</think>", "", raw_html_output, flags=re.DOTALL | re.IGNORECASE
    )
    cleaned = re.sub(r"```html|
```", "", cleaned, flags=re.IGNORECASE)

    # پاک‌سازیِ کلماتِ توقفِ (Stop-words) کلیشه‌ایِ رباتیک
    cliches = [
        r"\bدر نتیجه،\b",
        r"\bبه طور کلی،\b",
        r"\bبنابراین،\b",
        r"\bهمان‌طور که گفته شد،\b",
        r"\bهمان‌گونه که می‌دانید،\b",
        r"\btherefore\b",
        r"\bconclusion\b",
        r"\bsummary\b",
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
    """
    خلاصه‌سازِ ایمنِ کانتکست:
    به جای ارسالِ کلِ متنِ قبلی، صرفاً یک گزارشِ یک‌خطی از تیترهای نگارش‌یافته می‌سازد
    تا نویسنده دچارِ 'سندرومِ تکرارِ طوطی‌وار' نشود.
    """
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
            '      "core_thesis": "یک پاراگرافِ ۲ خطیِ پیوسته و پرمغز که در آن تمامِ حقایقِ علمی، تاریخی و مشخصاتِ این تیتر به صورتِ یک متنِ یکپارچه روایت شده است"،\n'
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

        sys_anchor = (
            get_system_anchor(keyword)
            + " "
            "هرگز عنوان H2 را در ابتدای متن تکرار نکن. "
            "از کلی‌گویی و شروع پاراگراف‌ها با عباراتی مانند «همان‌طور که می‌دانید» پرهیز کن."
        )

        user_request = (
            f"بخشِ تحتِ نگارش: «{h2_title}»\n"
            f"زیرعنوان‌ها: {h3_str}\n"
            f"تزِ محتواییِ این بخش (این متن را بسط بده و به یک بدنه‌ی ژورنالیستیِ جذاب تبدیل کن):\n«{core_thesis}»\n\n"
            f"واژه‌نامه‌ی اختصاصیِ صنف:\n{glossary_str}\n\n"
            f"وضعیتِ پیشرفتِ مقاله:\n[{safe_history_report}]\n"
            "با نگاه به گزارشِ بالا، مطالبِ گفته شده در تیترهای قبل را مطلقاً تکرار نکن.\n\n"
            f"کلمه کلیدیِ هدف: {keyword} (یک بار در متن حل شود)\n"
            f"کلماتِ LSI: {lsi_str}\n\n"
            "قوانینِ حیاتی نگارش:\n"
            "۱. قفلِ ضد لکنت (Anti-Loop): پس از نگارشِ متن، بررسی کن که پاراگرافِ پایینی، کپیِ مضمونِ پاراگرافِ بالایی نباشد. تکرارِ یک جمله در انتهای دو پاراگرافِ متوالی، ممنوع است!\n"
            "۲. پرهیز از گرامرِ کهنه: از افعالِ زنده و پویای فارسی استفاده کن؛ بکارگیریِ کلماتی مثل 'طلبیدند' یا 'گردیدند' ممنوع است.\n"
            "۳. ممنوعیتِ ارجاعِ کلیشه‌ای: عباراتی مثل «برای کسب اطلاعات بیشتر به صفحه‌ی مربوطه مراجعه کنید» ننویس.\n"
            "۴. فرمت خروجی: متن بدنه داخل تگ <p>. حداکثر ۳ خط در هر پاراگراف. خروجی فقط کدهای HTML بدنه باشد."
        )

        messages = [
            {"role": "system", "content": sys_anchor},
            {"role": "user", "content": user_request},
        ]

        raw_html = await self.llm.generate(messages)
        return pure_tree_walker_sanitizer(raw_html)