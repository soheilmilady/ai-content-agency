import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


class WebResearcher:
    async def research(self, topic: str) -> dict:
        empty = {"urls": [], "headings": [], "keywords": []}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                search_response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": settings.SERPER_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={"q": topic},
                )
                search_response.raise_for_status()
                data = search_response.json()

                organic = data.get("organic", [])[:3]
                urls = [item["link"] for item in organic if item.get("link")]

                keywords = [
                    item.get("query", "")
                    for item in data.get("relatedSearches", [])
                    if item.get("query")
                ]

                headings: list[str] = []
                for url in urls:
                    try:
                        page_response = await client.get(
                            url,
                            follow_redirects=True,
                            headers={"User-Agent": "Mozilla/5.0"},
                        )
                        page_response.raise_for_status()
                        soup = BeautifulSoup(page_response.text, "html.parser")
                        for tag in soup.find_all(["h2", "h3"]):
                            text = tag.get_text(strip=True)
                            if text:
                                headings.append(text)
                    except Exception:
                        continue

                return {"urls": urls, "headings": headings, "keywords": keywords}
        except Exception:
            return empty
