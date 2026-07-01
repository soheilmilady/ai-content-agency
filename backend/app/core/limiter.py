from slowapi import Limiter
from slowapi.util import get_remote_address

GLOBAL_DAILY_LIMIT = "20/day"

def get_dynamic_daily_limit() -> str:
    return GLOBAL_DAILY_LIMIT

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
