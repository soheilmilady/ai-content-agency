import ipaddress
import socket
import urllib.parse


def is_safe_external_url(url: str) -> tuple[bool, str]:
    """
    Validates that a target URL is a legitimate, publicly accessible HTTP/HTTPS destination.
    Mitigates Server-Side Request Forgery (SSRF) targeting:
    - Loopback interfaces (127.0.0.0/8, ::1)
    - Cloud instance metadata endpoints (169.254.169.254, fe80::/10)
    - RFC 1918 Private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Local hostnames ('localhost', '0.0.0.0')
    """
    if not url or not isinstance(url, str):
        return False, "آدرس اینترنتی خالی یا نامعتبر است."

    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            return False, "فقط پروتکل‌های http و https مجاز هستند."

        hostname = parsed.hostname
        if not hostname:
            return False, "نام دامنه یا هاست در آدرس یافت نشد."

        hostname_lower = hostname.lower()
        if hostname_lower in ("localhost", "0.0.0.0", "broadcast"):
            return False, "دسترسی به سرورهای محلی و داخلی مجاز نیست."

        # Check if the hostname itself is a raw IP literal
        try:
            raw_ip = ipaddress.ip_address(hostname_lower)
            if (
                raw_ip.is_private
                or raw_ip.is_loopback
                or raw_ip.is_link_local
                or raw_ip.is_reserved
                or raw_ip.is_multicast
            ):
                return False, "دسترسی به آدرس‌های IP خصوصی و متادیتای کلود مسدود است."
        except ValueError:
            # Not a raw IP literal; proceed to DNS resolution
            pass

        # Resolve all DNS records to prevent DNS rebinding attacks to private subnets
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False, "امکان ارتباط با سرور مقصد وجود ندارد (خطای تحلیل DNS)."

        for item in addr_info:
            ip_str = item[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_reserved
                    or ip_obj.is_multicast
                ):
                    return False, "دامنه به شبکه داخلی یا متادیتای سیستم اشاره دارد و مسدود شد."
            except ValueError:
                return False, "آدرس IP نامعتبر است."

        return True, ""
    except Exception as exc:
        return False, f"خطای امنیتی در تحلیل آدرس: {exc}"
