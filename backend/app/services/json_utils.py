import json
import re


def parse_json_response(text: str | None) -> dict:
    if not text or not str(text).strip():
        raise ValueError("مدل پاسخی برنگرداند. API key یا نام مدل را بررسی کنید.")

    cleaned = str(text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(
            f"خروجی JSON معتبر نبود. نمونه پاسخ: {cleaned[:180]}"
        ) from None
