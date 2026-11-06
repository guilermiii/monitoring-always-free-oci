import os
import json
import pytest
from unittest.mock import patch

from app.services.api_usage_store import (
    save_persistent_usage,
    load_persistent_usage,
    rehydrate_redis_from_disk,
)
from app.services.cache import get_api_usage, record_api_calls


@pytest.mark.asyncio
async def test_save_and_load_persistent_usage(tmp_path):
    """Test saving usage to disk and loading it back."""
    test_file = str(tmp_path / "test_api_usage.json")

    with patch("app.services.api_usage_store.API_USAGE_PERSISTENCE_FILE", test_file):
        with patch("app.services.api_usage_store.PERSISTENT_DATA_DIR", str(tmp_path)):
            assert load_persistent_usage("2026-11-06") is None

            saved = save_persistent_usage(calls_today=350, calls_last_run=70, date_str="2026-11-06")
            assert saved is True
            assert os.path.isfile(test_file)

            data = load_persistent_usage("2026-11-06")
            assert data is not None
            assert data["calls_today"] == 350
            assert data["calls_last_run"] == 70


@pytest.mark.asyncio
async def test_rehydration_restores_redis_from_disk(mock_redis, tmp_path):
    """Test rehydrating Redis counter from disk when Redis is empty."""
    test_file = str(tmp_path / "test_api_usage.json")

    with patch("app.services.api_usage_store.API_USAGE_PERSISTENCE_FILE", test_file):
        with patch("app.services.api_usage_store.PERSISTENT_DATA_DIR", str(tmp_path)):
            from datetime import datetime, timezone
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Persist to disk first
            save_persistent_usage(calls_today=520, calls_last_run=104, date_str=today_str)

            # Redis starts empty
            today_key = f"oci:api_calls:{today_str}"
            assert await mock_redis.get(today_key) is None

            # Rehydrate
            rehydrated = await rehydrate_redis_from_disk(mock_redis)
            assert rehydrated is True

            # Verify Redis now contains the persisted count
            redis_val = await mock_redis.get(today_key)
            assert redis_val == "520"


@pytest.mark.asyncio
async def test_get_api_usage_recovers_from_disk(mock_redis, tmp_path):
    """Test get_api_usage recovers from disk store if Redis key was lost."""
    test_file = str(tmp_path / "test_api_usage.json")

    with patch("app.services.api_usage_store.API_USAGE_PERSISTENCE_FILE", test_file):
        with patch("app.services.api_usage_store.PERSISTENT_DATA_DIR", str(tmp_path)):
            with patch("app.services.cache.get_redis_client", return_value=mock_redis):
                from datetime import datetime, timezone
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                save_persistent_usage(calls_today=800, calls_last_run=50, date_str=today_str)

                # Ensure Redis is empty
                today_key = f"oci:api_calls:{today_str}"
                await mock_redis.delete(today_key)

                # get_api_usage should recover from disk
                usage = await get_api_usage()
                assert usage["calls_today"] == 800
                assert usage["calls_last_run"] == 50
                assert usage["percentage"] == 8.0
