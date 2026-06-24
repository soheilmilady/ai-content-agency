import json
from collections.abc import AsyncGenerator

import litellm

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
            "محدودیت درخواست Groq (rate limit). چند دقیقه صبر کنید یا مدل سبک‌تر انتخاب کنید."
        )

    if "must contain the word 'json'" in message:
        return ValueError(
            "خطای JSON mode از Groq. لطفاً backend را restart کنید تا آخرین نسخه کد بارگذاری شود."
        )

    return ValueError(f"خطای Groq ({model}): {exc}")


class LLMGateway:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.DEFAULT_LLM_MODEL

    def _resolve_model(self, model: str) -> str:
        if model.startswith("groq/"):
            return model
        return f"groq/{model}"

    def _completion_kwargs(
        self, messages: list[dict], stream: bool, json_mode: bool
    ) -> dict:
        kwargs: dict = {
            "model": self._resolve_model(self.model),
            "messages": messages,
            "api_key": settings.GROQ_API_KEY,
            "stream": stream,
            "temperature": 0.7,
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

        try:
            response = await litellm.acompletion(
                **self._completion_kwargs(messages, False, json_mode)
            )
        except json.JSONDecodeError as exc:
            raise _friendly_llm_error(self.model, exc) from exc
        except Exception as exc:
            raise _friendly_llm_error(self.model, exc) from exc

        content = response.choices[0].message.content
        if not content or not str(content).strip():
            raise ValueError(
                f"مدل {self.model} پاسخ خالی برگرداند. "
                "احتمالاً quota تمام شده یا مدل در دسترس نیست."
            )
        return str(content)

    async def _stream(
        self, messages: list[dict], json_mode: bool
    ) -> AsyncGenerator[str, None]:
        try:
            response = await litellm.acompletion(
                **self._completion_kwargs(messages, True, json_mode)
            )
        except json.JSONDecodeError as exc:
            raise _friendly_llm_error(self.model, exc) from exc
        except Exception as exc:
            raise _friendly_llm_error(self.model, exc) from exc

        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
