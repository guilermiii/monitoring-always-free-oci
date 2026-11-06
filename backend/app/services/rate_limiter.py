import time
import logging
from typing import Tuple, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import (
    RATE_LIMIT_PUBLIC_PER_MINUTE,
    RATE_LIMIT_LOGIN_PER_MINUTE,
)
from app.services import cache

logger = logging.getLogger("oci-monitor.rate_limiter")

PREFIX_RATELIMIT = "oci:ratelimit:"
PREFIX_LOGIN_FAILURES = "oci:auth:failed:"
LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes


def get_client_ip(request: Request) -> str:
    """
    Safely extracts client IP address, prioritizing standard proxy headers.
    """
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # Take the leftmost IP (client)
        parts = [p.strip() for p in x_forwarded_for.split(",") if p.strip()]
        if parts:
            return parts[0]

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


async def check_sliding_window_rate_limit(
    key_identifier: str,
    limit: int,
    window_seconds: int = 60
) -> Tuple[bool, int, int]:
    """
    Implements a sliding-window rate limit using Redis sorted sets (ZSET).
    Returns: (is_allowed, remaining_requests, reset_seconds)
    """
    try:
        client = cache.get_redis_client()
        now = time.time()
        clear_before = now - window_seconds
        redis_key = f"{PREFIX_RATELIMIT}{key_identifier}"

        # Atomic transaction pipeline
        pipeline = client.pipeline()
        pipeline.zremrangebyscore(redis_key, 0, clear_before)
        pipeline.zcard(redis_key)
        pipeline.expire(redis_key, window_seconds + 5)
        results = await pipeline.execute()

        current_count = results[1]

        if current_count >= limit:
            remaining = 0
            reset_seconds = int(window_seconds)
            return False, remaining, reset_seconds

        # Record this request
        member_id = f"{now}_{current_count}"
        await client.zadd(redis_key, {member_id: now})

        remaining = max(0, limit - current_count - 1)
        reset_seconds = int(window_seconds)
        return True, remaining, reset_seconds

    except Exception as e:
        logger.warning(f"Rate limiting check failed (failing open): {e}")
        # Fail open if Redis has a transient issue
        return True, limit, 60


async def check_login_brute_force(client_ip: str) -> Tuple[bool, int]:
    """
    Checks if client IP is currently locked out due to multiple failed login attempts.
    Returns: (is_locked_out, remaining_lockout_seconds)
    """
    try:
        client = cache.get_redis_client()
        key = f"{PREFIX_LOGIN_FAILURES}{client_ip}"
        failed_count_raw = await client.get(key)

        if failed_count_raw:
            failed_count = int(failed_count_raw)
            if failed_count >= LOGIN_LOCKOUT_THRESHOLD:
                ttl = await client.ttl(key)
                return True, max(1, ttl)

        return False, 0
    except Exception as e:
        logger.warning(f"Error checking login brute force lock: {e}")
        return False, 0


async def record_login_failure(client_ip: str) -> int:
    """
    Increments failed login counter for client IP with 15 minutes TTL.
    Returns current failure count.
    """
    try:
        client = cache.get_redis_client()
        key = f"{PREFIX_LOGIN_FAILURES}{client_ip}"
        pipeline = client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, LOGIN_LOCKOUT_SECONDS)
        results = await pipeline.execute()
        return results[0]
    except Exception as e:
        logger.warning(f"Error recording login failure: {e}")
        return 1


async def clear_login_failures(client_ip: str) -> None:
    """Clears failed login counter upon successful authentication."""
    try:
        client = cache.get_redis_client()
        key = f"{PREFIX_LOGIN_FAILURES}{client_ip}"
        await client.delete(key)
    except Exception as e:
        logger.warning(f"Error clearing login failures: {e}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global middleware enforcing rate limits on public API endpoints to prevent flooding.
    Skips internal Kubernetes probes and Prometheus scrape endpoint.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Internal and non-metered paths
        if (
            path.startswith("/livez")
            or path.startswith("/readyz")
            or path.startswith("/startupz")
            or path.startswith("/healthz")
            or path.startswith("/metrics")
            or path == "/"
            or path.startswith("/docs")
            or path.startswith("/openapi.json")
        ):
            return await call_next(request)

        # Check rate limits for API paths
        if path.startswith("/api/v1"):
            client_ip = get_client_ip(request)

            # Route-specific limit: login gets stricter limit
            if path == "/api/v1/auth/login":
                limit = RATE_LIMIT_LOGIN_PER_MINUTE
                scope = f"auth:{client_ip}"
            else:
                limit = RATE_LIMIT_PUBLIC_PER_MINUTE
                scope = f"api:{client_ip}"

            allowed, remaining, reset = await check_sliding_window_rate_limit(
                scope,
                limit=limit,
                window_seconds=60
            )

            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Limite de requisições excedido. Por favor, aguarde antes de tentar novamente.",
                        "retry_after_seconds": reset
                    },
                    headers={
                        "Retry-After": str(reset),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset),
                    }
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset)
            return response

        return await call_next(request)
