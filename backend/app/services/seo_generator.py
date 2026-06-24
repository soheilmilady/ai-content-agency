from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


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
                    "You are an SEO expert writing Persian content. "
                    "Return ONLY valid JSON with double-quoted keys and strings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\n"
                    f"Focus keyword: {keyword}\n"
                    f"Competitor headings: {headings}\n"
                    "Build JSON with this exact structure:\n"
                    "{\n"
                    '  "h1": "main title including keyword",\n'
                    '  "meta_description": "150-160 chars meta",\n'
                    '  "sections": [\n'
                    '    {"h2": "section title", "h3_list": ["sub 1", "sub 2"], '
                    '"key_points": ["point 1"]}\n'
                    "  ],\n"
                    '  "lsi_keywords": ["related 1", "related 2"]\n'
                    "}\n"
                    "Use Persian text inside values. Minimum 5 H2 sections."
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
                    "تو یک نویسنده محتوای حرفه‌ای فارسی هستی. "
                    "متن روان، طبیعی و بدون ترجمه مستقیم بنویس."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"برای بخش '{h2_title}' یک پاراگراف ۱۵۰ تا ۲۵۰ کلمه‌ای بنویس.\n"
                    f"نکات مهم: {key_points}\n"
                    f"کلمه کلیدی اصلی را یک بار در این بخش استفاده کن: {keyword}\n"
                    f"کلمات مرتبط را طبیعی استفاده کن: {lsi_keywords}\n"
                    "جملات زیر ۲۵ کلمه باشند.\n"
                    "پاراگراف‌ها زیر ۳ خط باشند.\n"
                    "فقط متن HTML بدون تگ‌های اضافه برگردان (از h3 و p استفاده کن)."
                ),
            },
        ]
        return await self.llm.generate(messages)
