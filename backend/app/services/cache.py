import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.config import (
    REDIS_URL,
    CACHE_TTL_SECONDS,
    OCI_API_DAILY_LIMIT,
    OCI_API_RATE_LIMIT_PER_MIN,
)
from app.services.oci_collector import get_status_color
from app.services.api_usage_store import (
    save_persistent_usage,
    load_persistent_usage,
)

logger = logging.getLogger(__name__)

KEY_SUMMARY = "oci:free_tier:summary"
KEY_VOLUMES = "oci:free_tier:volumes"
KEY_NETWORK = "oci:free_tier:network"
KEY_DATABASE = "oci:free_tier:database"
KEY_INSTANCES = "oci:free_tier:instances"
KEY_STALE_BACKUP = "oci:free_tier:summary:backup"
KEY_API_CALLS_PREFIX = "oci:api_calls"
KEY_API_CALLS_LAST_RUN = "oci:api_calls:last_run"

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def ping_redis() -> bool:
    try:
        client = get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis ping failed: {e}")
        return False


async def get_cached_summary() -> Optional[Dict[str, Any]]:
    try:
        client = get_redis_client()
        raw = await client.get(KEY_SUMMARY)
        if raw:
            return json.loads(raw)
        # Try stale backup if main expired
        stale = await client.get(KEY_STALE_BACKUP)
        if stale:
            data = json.loads(stale)
            data["stale"] = True
            return data
    except Exception as e:
        logger.error(f"Error reading summary from Redis: {e}")
    return None


async def set_cached_summary(data: Dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        client = get_redis_client()
        raw = json.dumps(data)
        await client.set(KEY_SUMMARY, raw, ex=ttl)
        # Also store long-lived stale backup
        await client.set(KEY_STALE_BACKUP, raw, ex=86400 * 7)
        return True
    except Exception as e:
        logger.error(f"Error saving summary to Redis: {e}")
        return False


async def get_cached_volumes() -> Optional[List[Dict[str, Any]]]:
    try:
        client = get_redis_client()
        raw = await client.get(KEY_VOLUMES)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Error reading volumes from Redis: {e}")
    return None


async def set_cached_volumes(data: List[Dict[str, Any]], ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        client = get_redis_client()
        raw = json.dumps(data)
        await client.set(KEY_VOLUMES, raw, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error saving volumes to Redis: {e}")
        return False


async def get_cached_network() -> Optional[Dict[str, Any]]:
    try:
        client = get_redis_client()
        raw = await client.get(KEY_NETWORK)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Error reading network inventory from Redis: {e}")
    return None


async def set_cached_network(data: Dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        client = get_redis_client()
        raw = json.dumps(data)
        await client.set(KEY_NETWORK, raw, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error saving network inventory to Redis: {e}")
        return False


async def get_cached_database() -> Optional[List[Dict[str, Any]]]:
    try:
        client = get_redis_client()
        raw = await client.get(KEY_DATABASE)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Error reading database inventory from Redis: {e}")
    return None


async def set_cached_database(data: List[Dict[str, Any]], ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        client = get_redis_client()
        raw = json.dumps(data)
        await client.set(KEY_DATABASE, raw, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error saving database inventory to Redis: {e}")
        return False


async def get_cached_instances() -> Optional[List[Dict[str, Any]]]:
    try:
        client = get_redis_client()
        raw = await client.get(KEY_INSTANCES)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Error reading compute instances from Redis: {e}")
    return None


async def set_cached_instances(data: List[Dict[str, Any]], ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        client = get_redis_client()
        raw = json.dumps(data)
        await client.set(KEY_INSTANCES, raw, ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Error saving compute instances to Redis: {e}")
        return False


async def record_api_calls(calls_count: int) -> Dict[str, Any]:
    """Records calls made during a collection run and returns updated daily quota status, persisting to disk."""
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    today_key = f"{KEY_API_CALLS_PREFIX}:{today_str}"
    calls_today = calls_count

    try:
        client = get_redis_client()
        calls_today = await client.incrby(today_key, calls_count)
        # 48h TTL in Redis
        await client.expire(today_key, 86400 * 2)
        await client.set(KEY_API_CALLS_LAST_RUN, str(calls_count), ex=86400 * 2)
    except Exception as e:
        logger.error(f"Error recording API calls in Redis: {e}")

    # Persist atomically to disk volume for survivability across restarts
    save_persistent_usage(calls_today=calls_today, calls_last_run=calls_count, date_str=today_str)

    percentage = round((calls_today / OCI_API_DAILY_LIMIT) * 100, 2) if OCI_API_DAILY_LIMIT > 0 else 0.0
    return {
        "calls_today": int(calls_today),
        "daily_limit": OCI_API_DAILY_LIMIT,
        "calls_last_run": calls_count,
        "rate_limit_per_minute": OCI_API_RATE_LIMIT_PER_MIN,
        "percentage": percentage,
        "status": get_status_color(percentage),
    }


async def get_api_usage(calls_last_run: Optional[int] = None) -> Dict[str, Any]:
    """Retrieves current daily API usage stats from Redis, falling back to persistent disk store."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_key = f"{KEY_API_CALLS_PREFIX}:{today_str}"
    calls_today = 0
    last_run = calls_last_run

    try:
        client = get_redis_client()
        raw_today = await client.get(today_key)
        if raw_today is not None:
            calls_today = int(raw_today)
        else:
            # Fallback to persistent disk if Redis was flushed/restarted
            saved = load_persistent_usage(today_str)
            if saved and "calls_today" in saved:
                calls_today = int(saved["calls_today"])
                # Re-seed Redis
                await client.set(today_key, str(calls_today), ex=86400 * 2)
                if last_run is None:
                    last_run = saved.get("calls_last_run", 0)
                    await client.set(KEY_API_CALLS_LAST_RUN, str(last_run), ex=86400 * 2)

        if last_run is None:
            raw_last = await client.get(KEY_API_CALLS_LAST_RUN)
            last_run = int(raw_last) if raw_last else 0
    except Exception as e:
        logger.error(f"Error getting API usage from Redis: {e}")
        # Fallback to disk if Redis is unreachable
        saved = load_persistent_usage(today_str)
        if saved:
            calls_today = saved.get("calls_today", 0)
            if last_run is None:
                last_run = saved.get("calls_last_run", 0)

    percentage = round((calls_today / OCI_API_DAILY_LIMIT) * 100, 2) if OCI_API_DAILY_LIMIT > 0 else 0.0
    return {
        "calls_today": int(calls_today),
        "daily_limit": OCI_API_DAILY_LIMIT,
        "calls_last_run": int(last_run or 0),
        "rate_limit_per_minute": OCI_API_RATE_LIMIT_PER_MIN,
        "percentage": percentage,
        "status": get_status_color(percentage),
    }
