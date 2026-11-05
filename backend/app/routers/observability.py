import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST

from app.models.schemas import (
    LivenessResponse,
    ReadinessResponse,
    StartupResponse,
    GeneralHealthResponse,
)
from app.services import cache
from app.services.prometheus import (
    get_latest_metrics,
    update_oci_prometheus_metrics,
)
from app.config import load_oci_config

logger = logging.getLogger("oci-monitor.observability")

router = APIRouter()

# Global startup flag tracked by FastAPI lifespan
_app_started: bool = False


def set_app_started(started: bool = True) -> None:
    global _app_started
    _app_started = started


def is_app_started() -> bool:
    return _app_started


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Exposes Prometheus metrics in standard text format (0.0.4) including HTTP metrics, runtime, and real-time OCI Always Free resource gauges.",
    tags=["Observability & Metrics"],
    responses={
        200: {
            "content": {"text/plain; version=0.0.4; charset=utf-8": {}},
            "description": "Standard Prometheus text metrics output",
        }
    },
)
async def get_metrics():
    """
    Scrape endpoint for Prometheus.
    Syncs the latest cached OCI summary metrics into gauges before rendering the text payload.
    """
    try:
        cached_summary = await cache.get_cached_summary()
        if cached_summary:
            update_oci_prometheus_metrics(cached_summary)
    except Exception as e:
        logger.warning(f"Error fetching cached summary for metrics update: {e}")

    metrics_data = get_latest_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


@router.get(
    "/livez",
    response_model=LivenessResponse,
    summary="Kubernetes Liveness Probe",
    description="Checks whether the application process is running and the event loop is responsive. "
                "Per Kubernetes best practices, does not check downstream services to avoid cascading pod restarts.",
    tags=["Kubernetes Probes"],
    responses={
        200: {"model": LivenessResponse, "description": "Pod is healthy and alive"},
    },
)
async def get_liveness():
    """Kubernetes Liveness Probe."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return LivenessResponse(
        status="alive",
        timestamp=now_iso,
    )


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    summary="Kubernetes Readiness Probe",
    description="Validates if the pod is ready to accept user and API traffic. "
                "Performs an active check of Redis connectivity and OCI configuration validity. "
                "Returns HTTP 200 when ready, or HTTP 503 if any required dependency is unavailable.",
    tags=["Kubernetes Probes"],
    responses={
        200: {"model": ReadinessResponse, "description": "Pod is ready to serve traffic"},
        503: {"model": ReadinessResponse, "description": "Pod is not ready (dependency failure)"},
    },
)
async def get_readiness():
    """Kubernetes Readiness Probe."""
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_ok = await cache.ping_redis()
    oci_ok = False
    details_list = []

    try:
        cfg = load_oci_config()
        oci_ok = bool(cfg.get("tenancy") and cfg.get("key_file"))
        if not oci_ok:
            details_list.append("OCI config missing tenancy or key_file")
    except Exception as e:
        details_list.append(f"OCI config load error: {str(e)}")

    if not redis_ok:
        details_list.append("Redis ping failed (unable to reach cache)")

    is_ready = redis_ok and oci_ok
    status_str = "ready" if is_ready else "not_ready"
    details_str = "; ".join(details_list) if details_list else None

    payload = ReadinessResponse(
        status=status_str,
        redis_connected=redis_ok,
        oci_configured=oci_ok,
        timestamp=now_iso,
        details=details_str,
    )

    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return payload


@router.get(
    "/startupz",
    response_model=StartupResponse,
    summary="Kubernetes Startup Probe",
    description="Informs the kubelet whether the application has finished its startup and initialization routines. "
                "Returns HTTP 200 once ready, or HTTP 503 while initialization is still in progress.",
    tags=["Kubernetes Probes"],
    responses={
        200: {"model": StartupResponse, "description": "Application startup complete"},
        503: {"model": StartupResponse, "description": "Application still initializing"},
    },
)
async def get_startup():
    """Kubernetes Startup Probe."""
    now_iso = datetime.now(timezone.utc).isoformat()
    started = is_app_started()

    payload = StartupResponse(
        status="started" if started else "starting",
        app_started=started,
        timestamp=now_iso,
    )

    if not started:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return payload


@router.get(
    "/healthz",
    response_model=GeneralHealthResponse,
    summary="General Health Probe",
    description="General health check endpoint for container orchestrators and load balancers.",
    tags=["Kubernetes Probes"],
    responses={
        200: {"model": GeneralHealthResponse, "description": "Application is healthy"},
        503: {"model": GeneralHealthResponse, "description": "Application is degraded"},
    },
)
async def get_healthz():
    """General health check endpoint."""
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_ok = await cache.ping_redis()
    oci_ok = False
    message = None

    try:
        cfg = load_oci_config()
        oci_ok = bool(cfg.get("tenancy") and cfg.get("key_file"))
    except Exception as e:
        message = str(e)

    healthy = redis_ok and oci_ok
    status_str = "healthy" if healthy else "degraded"

    payload = GeneralHealthResponse(
        status=status_str,
        redis_connected=redis_ok,
        oci_configured=oci_ok,
        timestamp=now_iso,
        message=message,
    )

    if not healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return payload
