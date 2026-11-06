import logging
import re
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("oci-monitor.bot_defense")

# Common malicious scanners, automated exploitation tools, and scrapers
SUSPICIOUS_UA_PATTERNS = [
    r"sqlmap",
    r"nikto",
    r"masscan",
    r"nmap",
    r"zgrab",
    r"gobuster",
    r"dirbuster",
    r"wpscan",
    r"acunetix",
    r"havij",
    r"nessus",
    r"openvas",
]

COMPILED_UA_REGEX = re.compile("|".join(SUSPICIOUS_UA_PATTERNS), re.IGNORECASE)


class BotDefenseMiddleware(BaseHTTPMiddleware):
    """
    Application-level bot mitigation middleware.
    Inspects request headers and immediately blocks suspicious automated tools,
    vulnerability scanners, and aggressive scrapers.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Whitelist internal Kubernetes probes and local metrics scrapes
        if (
            path.startswith("/livez")
            or path.startswith("/readyz")
            or path.startswith("/startupz")
            or path.startswith("/healthz")
            or path.startswith("/metrics")
        ):
            return await call_next(request)

        user_agent = request.headers.get("user-agent", "").strip()

        # 1. Block empty user-agent on API routes
        if path.startswith("/api/v1") and not user_agent:
            logger.warning(f"Blocked API request with empty User-Agent from {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Acesso não autorizado (Missing User-Agent header)."}
            )

        # 2. Block known malicious scanners and exploit kits
        if COMPILED_UA_REGEX.search(user_agent):
            logger.warning(f"Blocked scanner/bot '{user_agent}' on path '{path}'")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Acesso negado."}
            )

        return await call_next(request)
