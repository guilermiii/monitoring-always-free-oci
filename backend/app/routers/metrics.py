import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.schemas import (
    HealthResponse,
    SummaryResponse,
    VolumeDetail,
    NetworkInventoryResponse,
    DatabaseDetail,
)
from app.services import cache
from app.services import worker
from app.config import load_oci_config, PORTFOLIO_MODE
from app.services.security import (
    get_current_admin,
    get_optional_admin,
    mask_summary_data,
    mask_volumes_data,
    mask_network_inventory,
    mask_database_inventory,
)

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
async def get_summary(admin=Depends(get_optional_admin)):
    """
    Returns consolidated OCI Always Free summary metrics.
    Serves from Redis in <5ms. Triggers on-demand collection if cache is cold.
    If accessed by a public guest in portfolio mode, aggressively masks identifying metadata.
    """
    cached = await cache.get_cached_summary()
    if not cached:
        try:
            cached = await worker.collect_and_cache()
        except Exception as e:
            logger.error(f"Failed to fetch summary: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve OCI metrics: {str(e)}"
            )

    if admin is None and PORTFOLIO_MODE:
        return mask_summary_data(cached)

    return cached


@router.post("/refresh", response_model=SummaryResponse)
async def force_refresh(admin=Depends(get_current_admin)):
    """
    Forces an immediate on-demand refresh of all OCI metrics, updating the cache.
    Restricted to authenticated Administrator to prevent cloud API quota exhaustion.
    """
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
async def get_storage_volumes(admin=Depends(get_optional_admin)):
    """
    Returns detailed inventory of boot and block volumes with orphan status.
    Masks OCIDs and private display names for portfolio visitors.
    """
    cached = await cache.get_cached_volumes()
    if cached is None:
        try:
            await worker.collect_and_cache()
            cached = await cache.get_cached_volumes()
        except Exception as e:
            logger.error(f"Failed to fetch volumes inventory: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve storage volumes: {str(e)}"
            )

    data = cached or []
    if admin is None and PORTFOLIO_MODE:
        return mask_volumes_data(data)
    return data


@router.get("/network/inventory", response_model=NetworkInventoryResponse)
async def get_network_inventory(admin=Depends(get_optional_admin)):
    """
    Returns detailed inventory of VCNs, Public IPs, and Load Balancers.
    Masks IP addresses and resource OCIDs for portfolio visitors.
    """
    cached = await cache.get_cached_network()
    if cached is None:
        try:
            await worker.collect_and_cache()
            cached = await cache.get_cached_network()
        except Exception as e:
            logger.error(f"Failed to fetch network inventory: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve network inventory: {str(e)}"
            )

    data = cached or {"vcns": [], "public_ips": [], "unassigned_ips": [], "load_balancers": []}
    if admin is None and PORTFOLIO_MODE:
        return mask_network_inventory(data)
    return data


@router.get("/database/inventory", response_model=List[DatabaseDetail])
async def get_database_inventory(admin=Depends(get_optional_admin)):
    """
    Returns detailed inventory of Autonomous Databases.
    Masks database OCIDs and names for portfolio visitors.
    """
    cached = await cache.get_cached_database()
    if cached is None:
        try:
            await worker.collect_and_cache()
            cached = await cache.get_cached_database()
        except Exception as e:
            logger.error(f"Failed to fetch database inventory: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to retrieve database inventory: {str(e)}"
            )

    data = cached or []
    if admin is None and PORTFOLIO_MODE:
        return mask_database_inventory(data)
    return data

