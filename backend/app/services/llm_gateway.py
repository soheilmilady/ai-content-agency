import asyncio
import json
from collections.abc import AsyncGenerator

import litellm
from litellm.exceptions import RateLimitError

from app.core.config import settings


def _friendly_llm_error(model: str, exc: Exception) -> ValueError:
    message = str(exc).lower()

    if isinstance(exc, json.JSONDecodeError):
        return ValueError(
            "پاسخ API Groq خالی یا نامعتبر بود. "
            "backend را restart کنید و کلید GROQ_API_KEY را در console.groq.com بررسی کنید."
        )

    if "decommissioned" in message or "model_decommissioned" in message:
        return ValueError(
            f"مدل «{model}» دیگر در Groq پشتیبانی نمی‌شود. "
            "مدل Llama 3.3 70B یا Llama 3.1 8B را انتخاب کنید."
        )

    if "invalid api key" in message or "invalid_api_key" in message:
        return ValueError(
            "کلید Groq نامعتبر است. در console.groq.com کلید را بررسی کنید "
            "(نیازی به تغییر فایل .env در این پروژه نیست مگر خودتان بخواهید)."
        )

    if "rate limit" in message or "429" in message:
        return ValueError(
            "محدودیت درخواست Groq (rate limit). ترافیک لحظه‌ای سرور بالاست؛ لطفاً چند ثانیه دیگر مجدداً تلاش کنید."
        )

    if "must contain the word 'json'" in message:
        return ValueError(
            "خطای JSON mode از Groq. لطفاً backend را restart کنید تا آخرین نسخه کد بارگذاری شود."
        )

    return ValueError(f"خطای Groq ({model}): {exc}")


class LLMGateway:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.DEFAULT_LLM_MODEL
        self.fallback_model = "groq/llama-3.1-8b-instant"

    def _resolve_model(self, target_model: str) -> str:
        if target_model.startswith("groq/"):
            return target_model
        return f"groq/{target_model}"

    def _completion_kwargs(
        self, target_model: str, messages: list[dict], stream: bool, json_mode: bool
    ) -> dict:
        kwargs: dict = {
            "model": self._resolve_model(target_model),
            "messages": messages,
            "api_key": settings.GROQ_API_KEY,
            "stream": stream,
            # <--- جادوی کنترلِ تخیل: دما از ۰.۷ به ۰.۲۵ کاهش یافت تا استعاره‌های فضایی نپراند!
            "temperature": 0.25,
            "max_tokens": 4000,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    async def generate(
        self,
        messages: list[dict],
        stream: bool = False,
        json_mode: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "کلید GROQ_API_KEY در backend تنظیم نشده. "
                "فایل backend/.env را بررسی کنید و سرویس را restart کنید."
            )

        if stream:
            return self._stream(messages, json_mode)

        active_model = self.model
        max_attempts = 2

        for attempt in range(max_attempts + 1):
            try:
                await asyncio.sleep(1.2)
                response = await litellm.acompletion(
                    **self._completion_kwargs(active_model, messages, False, json_mode)
                )
                content = response.choices[0].message.content
                if not content or not str(content).strip():
                    raise ValueError(
                        f"مدل {active_model} پاسخ خالی برگرداند. احتمالاً Quota تمام شده است."
                    )
                return str(content)

            except (RateLimitError, Exception) as exc:
                err_str = str(exc).lower()
                is_rate_limit = (
                    isinstance(exc, RateLimitError)
                    or "429" in err_str
                    or "rate limit" in err_str
                )

                if is_rate_limit:
                    if attempt == max_attempts:
                        if active_model != self.fallback_model:
                            active_model = self.fallback_model
                            await asyncio.sleep(4.0)
                            try:
                                fallback_res = await litellm.acompletion(
                                    **self._completion_kwargs(
                                        active_model, messages, False, json_mode
                                    )
                                )
                                return str(
                                    fallback_res.choices[0].message.content or ""
                                )
                            except Exception as fallback_exc:
                                raise _friendly_llm_error(
                                    active_model, fallback_exc
                                ) from fallback_exc

                    await asyncio.sleep((attempt + 1) * 2.5)
                    continue

                raise _friendly_llm_error(active_model, exc) from exc

        return ""

    async def _stream(
        self, messages: list[dict], json_mode: bool
    ) -> AsyncGenerator[str, None]:
        active_model = self.model
        response = None

        for attempt in range(2):
            try:
                await asyncio.sleep(1.0)
                response = await litellm.acompletion(
                    **self._completion_kwargs(active_model, messages, True, json_mode)
                )
                break
            except (RateLimitError, Exception) as exc:
                err_str = str(exc).lower()
                if (
                    isinstance(exc, RateLimitError)
                    or "429" in err_str
                    or "rate limit" in err_str
                ):
                    if attempt == 0 and active_model != self.fallback_model:
                        active_model = self.fallback_model
                        await asyncio.sleep(3.0)
                        continue
                    await asyncio.sleep(2.0)
                else:
                    raise _friendly_llm_error(active_model, exc) from exc

        if not response:
            raise ValueError(
                "ترافیک لحظه‌ایِ Groq در بالاترین حد است؛ لطفاً ۳۰ ثانیه دیگر مجدداً تلاش کنید."
            )

        try:
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception:
            pass