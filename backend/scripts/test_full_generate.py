import asyncio

from app.services.llm_gateway import LLMGateway
from app.services.seo_critic import SEOCritic
from app.services.seo_generator import SEOGenerator
from app.services.web_researcher import WebResearcher


async def main() -> None:
    topic = "راهنمای سئو محتوا"
    keyword = "سئو محتوا"
    llm = LLMGateway(model="llama-3.3-70b-versatile")
    researcher = WebResearcher()
    generator = SEOGenerator(llm)
    critic = SEOCritic(llm)

    try:
        research = await researcher.research(topic)
        print("research headings", len(research.get("headings", [])))
        outline = await generator.generate_outline(topic, keyword, research)
        print("outline sections", len(outline.get("sections", [])))
        sections_html: list[str] = []
        for section in outline.get("sections", []):
            html = await generator.draft_section(
                section["h2"],
                section.get("key_points", []),
                keyword,
                outline.get("lsi_keywords", []),
            )
            sections_html.append(html)
        parts = [f"<h1>{outline['h1']}</h1>"]
        for section, html in zip(outline.get("sections", []), sections_html):
            parts.append(f"<h2>{section['h2']}</h2>")
            parts.append(html)
        full = "".join(parts)
        print("content len", len(full))
        audit = await critic.audit(full, keyword)
        print("audit score", audit.get("score"))
        print("SUCCESS")
    except Exception as exc:
        print("FAIL", type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())
