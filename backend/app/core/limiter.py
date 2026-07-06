from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.session import SessionLocal
from app.models.setting import SystemSetting
from functools import lru_cache
import time

GLOBAL_DAILY_LIMIT = "20/day"

@lru_cache(maxsize=1)
def _get_cached_limit(ttl_hash: int) -> str:
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "global_daily_rate_limit").first()
        return setting.value if setting else GLOBAL_DAILY_LIMIT
    except Exception:
        return GLOBAL_DAILY_LIMIT
    finally:
        db.close()

def get_dynamic_daily_limit() -> str:
    # 30-second TTL
    ttl_hash = round(time.time() / 30)
    return _get_cached_limit(ttl_hash)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
