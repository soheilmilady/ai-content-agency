from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

PERSIAN_SYSTEM = (
    "تمام خروجی را فقط و فقط به زبان فارسی روان و رسمی بنویس. "
    "از هیچ کلمه‌ای به زبان ترکی، عربی، فرانسوی یا هر زبان دیگری استفاده نکن. "
    "اصطلاحات فنی رایج مانند کلدبرو، اسپرسو، فرنچ‌پرس قابل قبول هستند. "
    "هرگز کلمات غیرفارسی مانند ayrıca، también، aussi را به کار نبر."
)


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
                    '      "h2": "عنوان بخش اصلی (منحصربه‌فرد و متفاوت از H3)",\n'
                    '      "h3_list": ["زیرعنوان متفاوت ۱", "زیرعنوان متفاوت ۲"],\n'
                    '      "key_points": ["نکته مهم ۱", "نکته مهم ۲", "نکته مهم ۳"]\n'
                    '    }\n'
                    "  ],\n"
                    '  "lsi_keywords": ["کلمه مرتبط ۱", "کلمه مرتبط ۲", "کلمه مرتبط ۳"]\n'
                    "}\n\n"
                    "قوانین مهم:\n"
                    "- حداقل ۵ بخش H2 بساز\n"
                    "- عنوان H2 و H3 های هر بخش باید کاملاً متفاوت از هم باشند\n"
                    "- هیچ دو بخشی عنوان یکسان نداشته باشند\n"
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
                    "متن روان، طبیعی و کاملاً اصیل بنویس. "
                    "هرگز عنوان H2 را داخل متن تکرار نکن."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"برای بخش با عنوان «{h2_title}» متن کامل بنویس.\n\n"
                    f"نکات محتوایی که باید پوشش داده شوند: {key_points}\n"
                    f"کلمه کلیدی اصلی (یک بار به طور طبیعی استفاده کن): {keyword}\n"
                    f"کلمات مرتبط (طبیعی و پراکنده استفاده کن): {lsi_keywords}\n\n"
                    "قوانین نگارش:\n"
                    "- طول کل متن: ۱۵۰ تا ۲۵۰ کلمه فارسی\n"
                    "- هر جمله زیر ۲۵ کلمه باشد\n"
                    "- هر پاراگراف حداکثر ۳ خط باشد\n"
                    "- عنوان بخش را در ابتدا تکرار نکن\n"
                    "- فقط تگ‌های <h3> و <p> استفاده کن\n"
                    "- هیچ کلمه غیرفارسی (به جز اصطلاحات فنی) ننویس\n\n"
                    "فقط HTML خروجی بده، بدون توضیح اضافه."
                ),
            },
        ]
        return await self.llm.generate(messages)