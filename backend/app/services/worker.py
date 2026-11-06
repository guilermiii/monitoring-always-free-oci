import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from app.config import load_oci_config, REFRESH_INTERVAL_SECONDS
from app.services.oci_collector import OCICollector
from app.services.cache import (
    set_cached_summary,
    set_cached_volumes,
    set_cached_network,
    set_cached_database,
    set_cached_instances,
    record_api_calls,
)

logger = logging.getLogger(__name__)

_worker_task = None


async def collect_and_cache() -> Dict[str, Any]:
    """
    Executes OCI collection in an executor thread (to avoid blocking async loop)
    and saves the results into Redis.
    """
    logger.info("Starting OCI metrics collection...")
    try:
        cfg = load_oci_config()
        collector = OCICollector(cfg)

        # Run synchronous OCI SDK calls in asyncio thread pool
        loop = asyncio.get_running_loop()
        summary, volumes, network, databases, instances = await loop.run_in_executor(None, collector.collect)

        # Record API calls in Redis and attach api_usage to summary
        api_usage = await record_api_calls(collector.api_calls_count)
        summary["api_usage"] = api_usage

        await set_cached_summary(summary)
        await set_cached_volumes(volumes)
        await set_cached_network(network)
        await set_cached_database(databases)
        await set_cached_instances(instances)
        logger.info(f"Successfully updated OCI metrics in Redis (API calls this run: {collector.api_calls_count}).")
        return summary
    except Exception as e:
        logger.error(f"Failed to collect OCI metrics: {e}", exc_info=True)
        raise


async def start_background_worker():
    """Background worker that periodically refreshes the cache."""
    logger.info(f"Background worker started (interval: {REFRESH_INTERVAL_SECONDS}s).")
    # Immediate initial collection
    try:
        await collect_and_cache()
    except Exception as e:
        logger.warning(f"Initial background collection failed: {e}")

    while True:
        try:
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
            await collect_and_cache()
        except asyncio.CancelledError:
            logger.info("Background worker cancelled.")
            break
        except Exception as e:
            logger.error(f"Error during background worker execution: {e}")
