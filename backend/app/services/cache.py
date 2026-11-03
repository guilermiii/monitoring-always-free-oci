import json
import logging
from typing import Optional, Dict, Any, List
from app.config import REDIS_URL, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

KEY_SUMMARY = "oci:free_tier:summary"
KEY_VOLUMES = "oci:free_tier:volumes"
KEY_NETWORK = "oci:free_tier:network"
KEY_DATABASE = "oci:free_tier:database"
KEY_STALE_BACKUP = "oci:free_tier:summary:backup"

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
