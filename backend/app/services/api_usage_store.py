import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.config import (
    PERSISTENT_DATA_DIR,
    API_USAGE_PERSISTENCE_FILE,
)

logger = logging.getLogger("oci-monitor.api_usage_store")


def _ensure_data_dir():
    try:
        os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create persistent data dir {PERSISTENT_DATA_DIR}: {e}")


def load_all_history() -> Dict[str, Any]:
    """Loads all historical API usage records from disk."""
    if not os.path.isfile(API_USAGE_PERSISTENCE_FILE):
        return {}
    try:
        with open(API_USAGE_PERSISTENCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read API usage persistence file: {e}")
        return {}


def load_persistent_usage(date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Loads API usage for a specific date (defaults to today UTC)."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    history = load_all_history()
    return history.get(date_str)


def save_persistent_usage(calls_today: int, calls_last_run: int, date_str: Optional[str] = None) -> bool:
    """
    Atomically persists today's API usage to disk.
    Uses atomic write via temporary file to prevent corruption on crash.
    """
    _ensure_data_dir()
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        history = load_all_history()
        history[date_str] = {
            "calls_today": int(calls_today),
            "calls_last_run": int(calls_last_run),
            "last_updated": now_iso,
        }

        temp_file = f"{API_USAGE_PERSISTENCE_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        os.replace(temp_file, API_USAGE_PERSISTENCE_FILE)
        return True
    except Exception as e:
        logger.error(f"Failed to persist API usage to disk: {e}")
        return False


async def rehydrate_redis_from_disk(redis_client) -> bool:
    """
    Rehydrates today's API usage counter in Redis from disk if Redis was restarted or cold.
    Called on FastAPI application startup.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_key = f"oci:api_calls:{today_str}"
    key_last_run = "oci:api_calls:last_run"

    try:
        existing = await redis_client.get(today_key)
        if existing is not None:
            logger.info(f"Redis already contains API quota for today: {existing} calls.")
            return True

        # Not in Redis - check persistent disk
        saved = load_persistent_usage(today_str)
        if saved and "calls_today" in saved:
            calls_today = saved["calls_today"]
            calls_last_run = saved.get("calls_last_run", 0)
            await redis_client.set(today_key, str(calls_today), ex=86400 * 2)
            await redis_client.set(key_last_run, str(calls_last_run), ex=86400 * 2)
            logger.info(f"Successfully restored API quota from disk into Redis: {calls_today} calls today.")
            return True
        else:
            logger.info("No persistent API quota history found for today on disk; starting fresh.")
            return False
    except Exception as e:
        logger.warning(f"Error during Redis API usage rehydration: {e}")
        return False
