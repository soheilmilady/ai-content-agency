import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.deps import get_current_user
from app.core.limiter import limiter, get_dynamic_daily_limit
from app.models.user import User
from app.schemas.seo import ClusterRequest, ClusterResponse
from app.services.json_utils import parse_json_response
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalize_cluster_data(parsed: Any) -> dict[str, Any]:
    """تبدیل منعطف خروجی‌های ساختاریافته هوش مصنوعی به قالب معتبر ClusterResponse."""
    if isinstance(parsed, list):
        return {"clusters": parsed}
    if isinstance(parsed, dict):
        if "clusters" in parsed and isinstance(parsed["clusters"], list):
            return parsed
        for key in ("topics", "topic_clusters", "items", "data", "categories", "results"):
            if key in parsed and isinstance(parsed[key], list):
                return {"clusters": parsed[key]}
        if "cluster_name" in parsed or "pillar_keyword" in parsed:
            return {"clusters": [parsed]}
    return {"clusters": []}


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
        "لیستی از کلمات کلیدی کشف شده به تو داده می‌شود. وظیفه تو خوشه‌بندی معنایی (Topic Clustering) این کلمات برای جلوگیری از Keyword Cannibalization و ایجاد بریف استراتژی محتوا است.\n"
        "قوانین:\n"
        "۱. کلماتی که نیت جستجوی (Search Intent) یکسانی دارند را در یک خوشه قرار بده.\n"
        "۲. در هر خوشه، بهترین کلمه برای عنوان مقاله را به عنوان pillar_keyword انتخاب کن.\n"
        "۳. یک تیتر پیشنهادی جذاب و سئو شده برای H1 به فارسی روان بنویس (suggested_h1).\n"
        "۴. پرسونای مخاطب هدف را مشخص کن (target_audience مانند: خریداران، کاربران مبتدی، متخصصان).\n"
        "۵. سایر کلمات مرتبط در همان خوشه را به عنوان h2_keywords (زیرعنوان) قرار بده.\n"
        "۶. خروجی منحصراً باید یک JSON معتبر باشد.\n"
        "ساختار JSON مورد نیاز:\n"
        "{\n"
        '  "clusters": [\n'
        "    {\n"
        '      "cluster_name": "نام خوشه",\n'
        '      "pillar_keyword": "کلمه کلیدی اصلی",\n'
        '      "suggested_h1": "عنوان جذاب پیشنهادی H1",\n'
        '      "target_audience": "مخاطب هدف مقاله",\n'
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
        normalized = _normalize_cluster_data(parsed)
        return ClusterResponse(**normalized)
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation/LLM error clustering keywords: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cluster keywords: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
