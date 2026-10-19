import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# نگاشت مدل‌های قدیمی به جدیدترین مدل‌های پایدار گوگل جمینای
MODEL_ALIASES: dict[str, str] = {
    "llama-3.3-70b-versatile": "gemini-3.5-flash",
    "llama-3.1-8b-instant": "gemini-3.5-flash-lite",
    "meta-llama/llama-4-scout-17b-16e-instruct": "gemini-3.1-flash-lite",
    "llama-3.1-70b-versatile": "gemini-3.5-flash",
    "gemini-2.5-flash": "gemini-3.5-flash",
    "gemini-2.5-pro": "gemini-3.5-flash",
}

API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _friendly_llm_error(model: str, exc: Exception) -> ValueError:
    message = str(exc).lower()

    if isinstance(exc, json.JSONDecodeError):
        return ValueError(
            "پاسخ API گوگل خالی یا نامعتبر بود. لطفاً مجدداً تلاش کنید."
        )

    if "api_key_invalid" in message or "invalid api key" in message:
        return ValueError(
            "کلید Google AI Studio (Gemini API Key) در سرور Render نامعتبر است یا ثبت نشده است. "
            "لطفاً در پنل Render -> Environment، متغیر GEMINI_API_KEY را بدون گیومه و فاصله با مقدار کلید ذخیره کنید."
        )

    if "429" in message or "resource_exhausted" in message or "rate limit" in message or "quota" in message:
        return ValueError(
            f"سقف درخواست روزانه (Quota) در پلن رایگان Google AI Studio برای مدل «{model}» تکمیل شده است. "
            "لطفاً از مدل‌های پایدار دیگر (مانند Gemini 3.7 Flash) استفاده فرمایید یا فردا تلاش کنید."
        )

    if "permission_denied" in message or "403" in message:
        return ValueError(
            "دسترسی به Google Gemini رد شد (403 Permission Denied). "
            "ممکن است ریجن یا آی‌پی سرور در گوگل محدود شده باشد یا کلید دسترسی به این مدل را نداشته باشد."
        )

    if "404" in message or "not_found" in message:
        return ValueError(
            f"مدل «{model}» در Google Gemini یافت نشد یا از دسترس خارج شده است."
        )

    if "503" in message or "500" in message or "unavailable" in message:
        return ValueError(
            "سرویس هوش مصنوعی گوگل موقتاً با بار کاری بالا مواجه است. چند ثانیه دیگر تلاش کنید."
        )

    return ValueError(f"خطای Google Gemini ({model}): {exc}")


def _build_gemini_payload(
    messages: list[dict[str, Any]],
    json_mode: bool = False,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue

        if role == "system":
            system_parts.append(str(content))
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": str(content)}]})
        else:
            contents.append({"role": "user", "parts": [{"text": str(content)}]})

    # در صورتی که محتوایی نباشد، یک پرامپت خالی قرار می‌دهیم تا ارور ندهد
    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Hello"}]})

    payload: dict[str, Any] = {"contents": contents}

    if system_parts:
        combined_system = "\n\n".join(system_parts).strip()
        payload["system_instruction"] = {
            "parts": [{"text": combined_system}]
        }

    generation_config: dict[str, Any] = {
        "temperature": 0.25 if json_mode else 0.45,
    }
    if max_tokens:
        generation_config["maxOutputTokens"] = max_tokens

    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload["generationConfig"] = generation_config
    return payload


class LLMGateway:
    def __init__(self, model: str | None = None) -> None:
        self.model = self._resolve_model(model or settings.DEFAULT_LLM_MODEL)
        self.fallback_model = "gemini-3.7-flash" if self.model != "gemini-3.7-flash" else "gemini-3.1-flash-lite"

    def _resolve_model(self, target_model: str) -> str:
        # پاکسازی پیشوندهای مختلف
        clean = (
            target_model.replace("groq/", "")
            .replace("gemini/", "")
            .replace("google/", "")
            .strip()
        )
        return MODEL_ALIASES.get(clean, clean)

    def _get_api_key(self) -> str:
        raw_key = settings.GEMINI_API_KEY or settings.GROQ_API_KEY
        if not raw_key:
            raise ValueError(
                "متغیر GEMINI_API_KEY در تنظیمات سرور (Render Environment Variables) یا فایل .env تنظیم نشده است."
            )
        clean_key = raw_key.strip().strip('"').strip("'")
        if clean_key.startswith("gsk_"):
            raise ValueError(
                "کلید تنظیم‌شده در متغیرهای محیطی متعلق به Groq (gsk_...) است! "
                "لطفاً در پنل Render متغیر GEMINI_API_KEY را با مقدار کلید Google AI Studio جایگزین نمایید."
            )
        return clean_key

    async def generate(
        self,
        messages: list[dict],
        stream: bool = False,
        json_mode: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        api_key = self._get_api_key()

        if stream:
            return self._stream(messages, json_mode)

        active_model = self.model
        max_attempts = 2

        for attempt in range(max_attempts + 1):
            try:
                url = f"{API_BASE_URL}/{active_model}:generateContent?key={api_key}"
                payload = _build_gemini_payload(messages, json_mode=json_mode)

                async with httpx.AsyncClient(timeout=45.0) as client:
                    response = await client.post(url, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError(f"مدل {active_model} هیچ کاندیدی برای پاسخ ارائه نداد.")

                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts or "text" not in parts[0]:
                        raise ValueError(f"مدل {active_model} پاسخ متنی خالی داد.")

                    return str(parts[0]["text"]).strip()

                # در صورت خطای نرخ ترافیک یا در دسترس نبودن
                err_text = response.text
                if response.status_code in (429, 503) or "resource_exhausted" in err_text.lower():
                    if attempt < max_attempts:
                        await asyncio.sleep(2.0 * (attempt + 1))
                        # در آخرین تلاش از مدل فال‌بک سبک استفاده کن
                        if attempt == max_attempts - 1 and active_model != self.fallback_model:
                            active_model = self.fallback_model
                        continue

                raise _friendly_llm_error(active_model, Exception(f"HTTP {response.status_code}: {err_text}"))

            except Exception as exc:
                if attempt < max_attempts and ("timeout" in str(exc).lower() or "503" in str(exc)):
                    await asyncio.sleep(2.0 * (attempt + 1))
                    active_model = self.fallback_model
                    continue
                raise _friendly_llm_error(active_model, exc) from exc

        return ""

    async def _stream(
        self, messages: list[dict], json_mode: bool
    ) -> AsyncGenerator[str, None]:
        api_key = self._get_api_key()
        active_model = self.model
        max_attempts = 2

        for attempt in range(max_attempts):
            url = f"{API_BASE_URL}/{active_model}:streamGenerateContent?alt=sse&key={api_key}"
            payload = _build_gemini_payload(messages, json_mode=json_mode)

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            err_body = await response.aread()
                            err_msg = err_body.decode(errors="ignore")
                            if response.status_code in (429, 503) and attempt == 0:
                                active_model = self.fallback_model
                                await asyncio.sleep(1.5)
                                continue
                            raise _friendly_llm_error(
                                active_model,
                                Exception(f"HTTP {response.status_code}: {err_msg}"),
                            )

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                raw_json = line[6:].strip()
                                if not raw_json or raw_json == "[DONE]":
                                    continue
                                try:
                                    chunk = json.loads(raw_json)
                                    candidates = chunk.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for part in parts:
                                            text = part.get("text")
                                            if text:
                                                yield text
                                except Exception as json_err:
                                    logger.debug(f"Chunk JSON parse error: {json_err}")
                        return

            except Exception as exc:
                if attempt == 0 and active_model != self.fallback_model:
                    active_model = self.fallback_model
                    await asyncio.sleep(2.0)
                    continue
                raise _friendly_llm_error(active_model, exc) from exc