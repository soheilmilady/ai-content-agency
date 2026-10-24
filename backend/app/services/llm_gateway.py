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
    exc_type_name = type(exc).__name__.lower()
    exc_str = str(exc)
    message = f"{exc_type_name} {exc_str}".lower()

    if isinstance(exc, json.JSONDecodeError):
        return ValueError(
            "پاسخ API گوگل خالی یا نامعتبر بود. لطفاً مجدداً تلاش کنید."
        )

    if isinstance(exc, httpx.TimeoutException) or "timeout" in exc_type_name or "timeout" in message:
        return ValueError(
            f"زمان پاسخ‌دهی سرور گوگل برای مدل «{model}» به پایان رسید (Timeout). "
            "لطفاً از مدل‌های پایدارتر (مانند Gemini 3.6 Flash یا Gemini 3.5 Flash) استفاده کنید."
        )

    if "api_key_invalid" in message or "invalid api key" in message:
        return ValueError(
            "کلید Google AI Studio (Gemini API Key) در سرور Render نامعتبر است یا ثبت نشده است. "
            "لطفاً در پنل Render -> Environment، متغیر GEMINI_API_KEY را بدون گیومه و فاصله با مقدار کلید ذخیره کنید."
        )

    if "429" in message or "resource_exhausted" in message or "rate limit" in message or "quota" in message:
        return ValueError(
            f"سقف درخواست روزانه (Quota) در پلن رایگان Google AI Studio برای مدل «{model}» تکمیل شده است. "
            "لطفاً از مدل‌های پایدار دیگر (مانند Gemini 3.6 Flash یا Gemini 3.5 Flash) استفاده فرمایید یا فردا تلاش کنید."
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

    err_details = exc_str.strip() or exc_type_name
    return ValueError(f"خطای Google Gemini ({model}): {err_details}")


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

    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    if max_tokens is not None:
        generation_config["max_output_tokens"] = max_tokens

    payload["generationConfig"] = generation_config
    return payload


class LLMGateway:
    def __init__(self, model: str | None = None):
        raw_model = model or getattr(settings, "DEFAULT_LLM_MODEL", "gemini-3.6-flash")
        self.model = MODEL_ALIASES.get(raw_model, raw_model)
        self.fallback_model = "gemini-3.6-flash"

    def _get_api_key(self) -> str:
        api_key = getattr(settings, "GEMINI_API_KEY", "").strip("\"' \t\r\n")
        if not api_key:
            raise ValueError(
                "متغیر محیطی GEMINI_API_KEY تنظیم نشده است. "
                "لطفاً کلید API را از Google AI Studio دریافت و در فایل .env یا تنظیمات سرور ثبت کنید."
            )
        return api_key

    async def generate(
        self,
        messages: list[dict],
        json_mode: bool = False,
        stream: bool = False,
    ) -> Any:
        if stream:
            return self._stream(messages, json_mode)
        return await self._generate_no_stream(messages, json_mode)

    async def _generate_no_stream(self, messages: list[dict], json_mode: bool) -> str:
        api_key = self._get_api_key()
        active_model = self.model
        max_attempts = 2

        for attempt in range(max_attempts + 1):
            try:
                # Security: Pass API key via x-goog-api-key header instead of URL query parameter
                url = f"{API_BASE_URL}/{active_model}:generateContent"
                headers = {
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                }
                payload = _build_gemini_payload(messages, json_mode=json_mode)

                async with httpx.AsyncClient(timeout=25.0 if attempt == 0 else 40.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

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
                is_timeout = isinstance(exc, httpx.TimeoutException) or "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower()
                if attempt < max_attempts and (is_timeout or "503" in str(exc)):
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
            # Security: Pass API key via x-goog-api-key header instead of URL query parameter
            url = f"{API_BASE_URL}/{active_model}:streamGenerateContent?alt=sse"
            headers = {
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            }
            payload = _build_gemini_payload(messages, json_mode=json_mode)

            try:
                async with httpx.AsyncClient(timeout=30.0 if attempt == 0 else 60.0) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as response:
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
                                        if parts and "text" in parts[0]:
                                            yield parts[0]["text"]
                                except json.JSONDecodeError:
                                    continue
                return

            except Exception as exc:
                is_timeout = isinstance(exc, httpx.TimeoutException) or "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower()
                if attempt < max_attempts - 1 and (is_timeout or "503" in str(exc)):
                    await asyncio.sleep(2.0)
                    active_model = self.fallback_model
                    continue
                raise _friendly_llm_error(active_model, exc) from exc
