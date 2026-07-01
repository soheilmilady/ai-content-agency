from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_dynamic_daily_limit(request: Request) -> str:
    return getattr(request.app.state, "global_limit", "20/day")

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
