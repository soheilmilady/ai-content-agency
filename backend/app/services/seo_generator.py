import re
from typing import Any
from bs4 import BeautifulSoup

from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

PERSIAN_SYSTEM = (
    "تو یک سردبیر، ژورنالیست صنعتی و ویراستار ارشد زبان فارسی هستی. "
    "قانون حیاتی: تمام متن باید ۱۰۰٪ به زبان فارسی اصیل، رسمی و روان نوشته شود. "
    "استفاده از کلمات انگلیسی، آلمانی، ترکی یا فینگلیش (مانند prepare, zwischen, Cold Brew, filter) در متن بدنه مطلقاً ممنوع است. "
    "همیشه معادل استاندارد فارسی آن‌ها (مانند: آماده‌سازی، بین، عصاره‌گیری سرد، فیلتر) را به کار ببر."
)

# کلمات غیرفارسی عجیبی که لاما گاهی وسط فارسی پرتاب می‌کند
_KNOWN_FOREIGN = re.compile(
    r"\b(ayrıca|también|aussi|льод|вкус|industria|melhor|популяр|"
    r"필요|また|também|además|également|inoltre|außerdem|также|"
    r"furthermore|however|therefore|moreover|zwischen|prepare)\b",
    re.IGNORECASE,
)


def sanitize_html_for_tiptap(raw_html: str) -> str:
    """
    ناجیِ کلماتِ بخار شده:
    تگ‌های غیرمجازی که LLM تولید کرده (مثل <pitcher> یا <container>) را باز می‌کند
    تا محتوای متنیِ داخلشان حفظ شود و TipTap آن‌ها را قورت ندهد.
    """
    text = _KNOWN_FOREIGN.sub("", raw_html)
    soup = BeautifulSoup(text, "html.parser")

    # لیست تگ‌های استانداردی که ادیتور TipTap در فرانت‌اند می‌فهمد
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
            # به جای حذف تگ، محتوایش را بیرون می‌کشد (unwrap)
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
                "قانون تداوم (Continuity): با توجه به حافظه بالا، مطالب، تعاریف اولیه و جملات بخش‌های قبل را تکرار نکن! "
                "متن این بخش را طوری شروع کن که ادامهٔ منطقی و جذابِ متنِ قبلی باشد."
            )

        messages = [
            {
                "role": "system",
                "content": (
                    PERSIAN_SYSTEM + " "
                    "تو یک ژورنالیستِ پخته، سردبیر و متخصص نگارشِ مقالاتِ بلندِ فارسی هستی. "
                    "لحن تو توصیفی، تحلیلی، غنی و ۱۰۰٪ انسانی است. "
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
                    "قوانینِ حیاتیِ کالیبراسیونِ متن (تخطی از این موارد ممنوع است):\n"
                    "۱. خلوص زبانی (Zero Code-Switching): متن باید به زبان فارسی اصیل و بدون کلمات بیگانه باشد. به جای کلمات لاتین مثل Cold Brew یا عصاره‌گیریِ prepare، معادل‌های دقیقِ فارسی (مانند: عصاره‌گیری سرد، دم‌آوری، آماده‌سازی، عبور از فیلتر) را به کار ببر. استفاده از کلمات آلمانی مثل zwischen جریمهٔ سنگین دارد!\n"
                    "۲. تنوع ریتم: ترکیبی متعادل از جملات کوتاه (۵ تا ۸ کلمه) و جملات مرکبِ زیبا (۱۵ تا ۲۰ کلمه) ایجاد کن تا متن آهنگِ طبیعیِ یک نویسندهٔ حرفه‌ای را پیدا کند.\n"
                    "۳. اعتدال در کلمات ربط: استفاده از کلمات متصل‌کننده (مانند: مضاف بر این، با این اوصاف، از سوی دیگر) مجاز است اما در کلِ این بخش، نهایتاً «فقط یک بار» از این کلمات استفاده کن! متن را تصنعی نکن.\n"
                    "۴. ممنوعیتِ ارجاعِ تنبلانه (No Lazy CTAs): تحت هیچ شرایطی در انتهای پاراگراف‌ها عبارات کلیشه‌ای مثل «برای کسب اطلاعات بیشتر به صفحه مربوطه مراجعه کنید» ننویس.\n"
                    "۵. ساختار بصری و تگ‌ها: متن بدنه را حتماً داخل تگ <p> قرار بده. حداکثر ۳ تا ۴ خط در هر پاراگراف. اگر نیاز به لیست بود از <ul>/<li> استفاده کن. خروجی فقط کدهای HTML بدنه باشد. از تولید تگ‌های من‌درآوردی مثل <container> یا <filter> خودداری کن!"
                ),
            },
        ]

        raw = await self.llm.generate(messages)
        return sanitize_html_for_tiptap(raw)