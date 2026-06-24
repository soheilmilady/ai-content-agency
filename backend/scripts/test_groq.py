import asyncio

from app.core.config import settings
from app.services.llm_gateway import LLMGateway
from app.services.seo_generator import SEOGenerator


async def main() -> None:
    print("key set:", bool(settings.GROQ_API_KEY))
    print("model:", settings.DEFAULT_LLM_MODEL)
    gw = LLMGateway()
    try:
        text = await gw.generate([{"role": "user", "content": "Say hi in one word"}])
        print("text ok:", text[:80])
    except Exception as exc:
        print("text err:", exc)
    try:
        text = await gw.generate(
            [{"role": "user", "content": 'Return JSON: {"ok": true}'}],
            json_mode=True,
        )
        print("json ok:", text[:120])
    except Exception as exc:
        print("json err:", exc)


async def test_model(model: str) -> None:
    print(f"\n--- {model} ---")
    gw = LLMGateway(model=model)
    gen = SEOGenerator(gw)
    try:
        outline = await gen.generate_outline(
            "test",
            "test",
            {"headings": [], "keywords": [], "urls": []},
        )
        print("sections:", len(outline.get("sections", [])))
    except Exception as exc:
        print("ERR:", type(exc).__name__, str(exc)[:160])


if __name__ == "__main__":
    asyncio.run(main())
    for name in (
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-70b-versatile",
    ):
        asyncio.run(test_model(name))
