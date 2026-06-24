from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway


class SEOCritic:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm or LLMGateway()

    async def audit(self, full_content: str, keyword: str) -> dict:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an SEO expert. Return ONLY valid JSON "
                    "with double-quoted keys."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyze this Persian content:\n{full_content}\n\n"
                    f"Focus keyword: {keyword}\n\n"
                    "Return JSON:\n"
                    "{\n"
                    '  "score": 85,\n'
                    '  "keyword_density": 2.0,\n'
                    '  "issues": ["issue 1"],\n'
                    '  "suggestions": ["suggestion 1"]\n'
                    "}"
                ),
            },
        ]
        raw = await self.llm.generate(messages, json_mode=True)
        return parse_json_response(raw)

    async def improve(self, full_content: str, keyword: str, issues: list[str]) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "تو یک متخصص سئو و نویسنده محتوای فارسی هستی. "
                    "متن را با رفع مشکلات بازنویسی کن. فقط HTML نهایی را برگردان."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"کلمه کلیدی: {keyword}\n\n"
                    f"مشکلات:\n{issues}\n\n"
                    f"متن فعلی:\n{full_content}\n\n"
                    "متن را بهبود بده و HTML کامل را برگردان."
                ),
            },
        ]
        return await self.llm.generate(messages)
