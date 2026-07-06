from typing import Annotated
import json
from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.seo import ClusterRequest, ClusterResponse
from app.services.llm_gateway import LLMGateway
from app.services.json_utils import parse_json_response

router = APIRouter()

@router.post("/cluster", response_model=ClusterResponse)
async def cluster_keywords(
    request: ClusterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not request.keywords:
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
        {"role": "user", "content": json.dumps(request.keywords, ensure_ascii=False)}
    ]
    
    try:
        raw_json = await llm.generate(messages, json_mode=True)
        parsed = parse_json_response(raw_json)
        return ClusterResponse(**parsed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cluster keywords: {str(e)}")
