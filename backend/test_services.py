
import asyncio
from app.services.web_researcher import WebResearcher

async def test():
    r = WebResearcher()
    result = await r.research("خرید قهوه عربیکا")
    print(result)

asyncio.run(test())