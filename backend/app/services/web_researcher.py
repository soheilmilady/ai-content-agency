import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


class WebResearcher:
    async def research(self, topic: str) -> dict:
        empty = {"urls": [], "headings": [], "keywords": [], "snippets": []}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:

                # ── مرحله ۱: جستجوی Serper ──────────────────────
                search_response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": settings.SERPER_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={"q": topic, "num": 10, "hl": "fa"},
                )
                search_response.raise_for_status()
                data = search_response.json()

                organic = data.get("organic", [])[:5]
                urls = [item["link"] for item in organic if item.get("link")]

                # snippets مستقیم از Serper — مهم‌ترین منبع facts
                snippets: list[str] = []
                for item in organic:
                    snippet = item.get("snippet", "").strip()
                    title = item.get("title", "").strip()
                    if snippet:
                        # عنوان + snippet = یک fact کامل
                        snippets.append(f"{title}: {snippet}" if title else snippet)

                # کلمات کلیدی مرتبط — فیلد درست "text" است
                keywords: list[str] = [
                    item.get("query") or item.get("text", "")
                    for item in data.get("relatedSearches", [])
                    if item.get("query") or item.get("text")
                ]

                # answerBox اگه وجود داشت — اطلاعات مستقیم گوگل
                answer_box = data.get("answerBox", {})
                if answer_box:
                    answer = (
                        answer_box.get("answer")
                        or answer_box.get("snippet")
                        or answer_box.get("snippetHighlighted", "")
                    )
                    if answer:
                        snippets.insert(0, f"[پاسخ مستقیم گوگل]: {answer}")

                # knowledgeGraph اگه وجود داشت
                kg = data.get("knowledgeGraph", {})
                if kg.get("description"):
                    snippets.insert(0, f"[دانش‌نامه]: {kg['description']}")

                # ── مرحله ۲: scraping صفحات ──────────────────────
                headings: list[str] = []
                page_snippets: list[str] = []

                for url in urls:
                    try:
                        page_response = await client.get(
                            url,
                            follow_redirects=True,
                            timeout=8.0,  # timeout کوتاه per-page
                            headers={
                                "User-Agent": (
                                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/120.0.0.0 Safari/537.36"
                                )
                            },
                        )
                        page_response.raise_for_status()
                        soup = BeautifulSoup(page_response.text, "html.parser")

                        # عناوین H2 و H3 برای outline
                        for tag in soup.find_all(["h2", "h3"]):
                            text = tag.get_text(strip=True)
                            if text and len(text) > 5:
                                headings.append(text)

                        # پاراگراف‌های متنی برای facts
                        paragraphs = soup.find_all("p")
                        for p in paragraphs[:8]:
                            text = p.get_text(strip=True)
                            # فقط پاراگراف‌های اطلاعاتی واقعی
                            if len(text) > 60:
                                page_snippets.append(text)

                    except Exception:
                        # اگه scraping fail شد، snippet خود Serper کافیه
                        continue

                # ترکیب: snippets Serper + محتوای صفحات
                all_snippets = snippets + page_snippets

                return {
                    "urls": urls,
                    "headings": headings,
                    "keywords": keywords,
                    "snippets": all_snippets,
                }

        except Exception:
            return empty