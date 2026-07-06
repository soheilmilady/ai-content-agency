import time
from functools import lru_cache
import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.setting import SystemSetting

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

def custom_rate_limit_key(request: Request) -> str:
    # 1. Try to limit by User ID if authenticated
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            sub = payload.get("sub")
            if sub:
                return f"user_{sub}"
        except Exception:
            pass

    # 2. Try X-Forwarded-For for proxy environments
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    # 3. Fallback to default remote address
    return get_remote_address(request)

limiter = Limiter(key_func=custom_rate_limit_key, default_limits=["200/minute"])
