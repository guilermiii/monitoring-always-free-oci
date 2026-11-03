import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import HealthResponse, SummaryResponse, VolumeDetail
from app.services import cache
from app.services import worker
from app.config import load_oci_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Health check endpoint for container orchestrators and monitoring."""
    redis_ok = await cache.ping_redis()
    oci_ok = False
    message = None

    try:
        cfg = load_oci_config()
        oci_ok = bool(cfg.get("tenancy") and cfg.get("key_file"))
    except Exception as e:
        message = str(e)

    overall_status = "healthy" if (redis_ok and oci_ok) else "degraded"
    return HealthResponse(
        status=overall_status,
        redis_connected=redis_ok,
        oci_configured=oci_ok,
        message=message
    )


@router.get("/summary", response_model=SummaryResponse)
async def get_summary():
    """
    Returns consolidated OCI Always Free summary metrics.
    Serves from Redis in <5ms. Triggers on-demand collection if cache is cold.
    """
    cached = await cache.get_cached_summary()
    if cached:
        return cached

    try:
        summary = await worker.collect_and_cache()
        return summary
    except Exception as e:
        logger.error(f"Failed to fetch summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to retrieve OCI metrics: {str(e)}"
        )


@router.post("/refresh", response_model=SummaryResponse)
async def force_refresh():
    """Forces an immediate on-demand refresh of all OCI metrics, updating the cache."""
    try:
        summary = await worker.collect_and_cache()
        return summary
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refresh failed: {str(e)}"
        )


@router.get("/storage/volumes", response_model=List[VolumeDetail])
async def get_storage_volumes():
    """Returns detailed inventory of boot and block volumes with orphan status."""
    cached = await cache.get_cached_volumes()
    if cached is not None:
        return cached

    try:
        await worker.collect_and_cache()
        cached = await cache.get_cached_volumes()
        return cached or []
    except Exception as e:
        logger.error(f"Failed to fetch volumes inventory: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to retrieve storage volumes: {str(e)}"
        )


@router.get("/network/inventory")
async def get_network_inventory():
    """Returns detailed inventory of VCNs, Public IPs, and Load Balancers."""
    cached = await cache.get_cached_network()
    if cached is not None:
        return cached

    try:
        await worker.collect_and_cache()
        cached = await cache.get_cached_network()
        return cached or {"vcns": [], "public_ips": [], "unassigned_ips": [], "load_balancers": []}
    except Exception as e:
        logger.error(f"Failed to fetch network inventory: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to retrieve network inventory: {str(e)}"
        )


@router.get("/database/inventory")
async def get_database_inventory():
    """Returns detailed inventory of Autonomous Databases."""
    cached = await cache.get_cached_database()
    if cached is not None:
        return cached

    try:
        await worker.collect_and_cache()
        cached = await cache.get_cached_database()
        return cached or []
    except Exception as e:
        logger.error(f"Failed to fetch database inventory: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to retrieve database inventory: {str(e)}"
        )
