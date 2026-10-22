import ipaddress
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

# Trusted proxy CIDRs (loopback, private container gateways in Docker/Render)
TRUSTED_PROXY_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
)


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


def get_safe_client_ip(request: Request) -> str:
    """
    Extracts client IP safely without allowing arbitrary X-Forwarded-For spoofing.
    X-Forwarded-For is only parsed when the direct peer is a trusted local/container proxy.
    """
    direct_ip = request.client.host if request.client else "127.0.0.1"

    is_trusted_peer = False
    try:
        direct_obj = ipaddress.ip_address(direct_ip)
        is_trusted_peer = any(direct_obj in net for net in TRUSTED_PROXY_NETWORKS)
    except ValueError:
        is_trusted_peer = False

    if is_trusted_peer:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip_candidate = forwarded.split(",")[0].strip()
            try:
                # Validate candidate IP structure
                ipaddress.ip_address(client_ip_candidate)
                return client_ip_candidate
            except ValueError:
                pass

    return direct_ip


def custom_rate_limit_key(request: Request) -> str:
    # 1. Limit by User ID if authenticated with a valid token
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

    # 2. Limit by hardened Client IP
    return get_safe_client_ip(request)


limiter = Limiter(key_func=custom_rate_limit_key, default_limits=["200/minute"])
