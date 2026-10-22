import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.deps import get_current_user
from app.core.limiter import limiter, get_dynamic_daily_limit
from app.models.user import User
from app.schemas.seo import ClusterRequest, ClusterResponse
from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/cluster", response_model=ClusterResponse)
@limiter.limit(get_dynamic_daily_limit)
async def cluster_keywords(
    request: Request,
    body: ClusterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not body.keywords:
        raise HTTPException(status_code=400, detail="Keywords list cannot be empty")

    llm = LLMGateway()

    prompt = (
        "تو یک استراتژیست ارشد سئو (SEO Strategist) هستی.\n"
        "لیستی از کلمات کلیدی کشف شده به تو داده می‌شود. وظیفه تو خوشه‌بندی معنایی (Topic Clustering) این کلمات برای جلوگیری از Keyword Cannibalization است.\n"
        "قوانین:\n"
        "۱. کلماتی که نیت جستجوی (Search Intent) یکسانی دارند را در یک خوشه قرار بده.\n"
        "۲. در هر خوشه، بهترین کلمه برای عنوان مقاله را به عنوان pillar_keyword انتخاب کن.\n"
        "۳. سایر کلمات مرتبط در همان خوشه را به عنوان h2_keywords (زیرعنوان) قرار بده.\n"
        "۴. خروجی منحصراً باید یک JSON معتبر باشد.\n"
        "ساختار JSON مورد نیاز:\n"
        "{\n"
        '  "clusters": [\n'
        "    {\n"
        '      "cluster_name": "نام خوشه",\n'
        '      "pillar_keyword": "کلمه کلیدی اصلی",\n'
        '      "h2_keywords": ["فرعی ۱", "فرعی ۲"],\n'
        '      "search_intent": "Informational | Transactional | Commercial",\n'
        '      "cannibalization_warning": "توضیح در صورت همپوشانی (اختیاری)"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(body.keywords, ensure_ascii=False)},
    ]

    try:
        raw_json = await llm.generate(messages, json_mode=True)
        parsed = parse_json_response(raw_json)
        return ClusterResponse(**parsed)
    except Exception as e:
        logger.error(f"Failed to cluster keywords: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="خطا در پردازش و خوشه‌بندی کلمات کلیدی توسط هوش مصنوعی. لطفاً مجدداً تلاش کنید."
        )
