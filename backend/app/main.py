import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers.metrics import router as metrics_router
from app.routers.observability import router as observability_router, set_app_started
from app.routers.auth import router as auth_router
from app.services.rate_limiter import RateLimitMiddleware
from app.services.bot_defense import BotDefenseMiddleware
from app.services.prometheus import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
from app.services.worker import start_background_worker
from app.services.cache import get_redis_client
from app.services.api_usage_store import rehydrate_redis_from_disk
from app.models.schemas import RootResponse
from app.config import ALLOWED_ORIGINS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("oci-monitor")

tags_metadata = [
    {
        "name": "Kubernetes Probes",
        "description": "Lifecycle probe endpoints for Kubernetes (Liveness, Readiness, Startup) and load balancers.",
    },
    {
        "name": "Observability & Metrics",
        "description": "Prometheus scrape endpoint exposing HTTP latency/requests and real-time OCI Always Free gauges.",
    },
    {
        "name": "Authentication",
        "description": "Single-user administrator login, session management, and brute-force protection.",
    },
    {
        "name": "metrics",
        "description": "OCI Always Free resources monitoring, cache summary, on-demand refresh, and detailed inventories.",
    },
    {
        "name": "General",
        "description": "Application index and API discovery links.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Rehydrate API quota from disk into Redis if Redis was restarted
    try:
        redis_client = get_redis_client()
        await rehydrate_redis_from_disk(redis_client)
    except Exception as e:
        logger.warning(f"Startup Redis rehydration check encountered an error: {e}")

    # Initialize background worker unless explicitly disabled
    disable_worker = os.getenv("DISABLE_BACKGROUND_WORKER", "false").lower() in ["1", "true", "yes"]
    worker_task = None
    if not disable_worker:
        worker_task = asyncio.create_task(start_background_worker())
        logger.info("Background worker task created.")

    # Mark application as fully started for startup probe
    set_app_started(True)
    logger.info("Application startup complete. Probes active.")

    yield

    # Shutdown: Cancel worker task and mark app as not started
    set_app_started(False)
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        logger.info("Background worker stopped.")


app = FastAPI(
    title="OCI Always Free Monitor API",
    version="1.0.0",
    description="Production-grade API for monitoring Oracle Cloud Infrastructure (OCI) Always Free tier resources, "
                "detecting orphan volumes/IPs, exposing Prometheus metrics, and supporting Kubernetes lifecycle probes.",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# CORS configuration supporting credentials (cookies)
if ALLOWED_ORIGINS == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Security & Flooding Mitigation Middlewares
app.add_middleware(RateLimitMiddleware)
app.add_middleware(BotDefenseMiddleware)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    """Measures latency and request counts for Prometheus scraping."""
    start_time = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        try:
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        except Exception:
            pass


# Register routers
app.include_router(observability_router)
app.include_router(auth_router)
app.include_router(metrics_router)


@app.get(
    "/",
    response_model=RootResponse,
    tags=["General"],
    summary="API Root Information",
    description="Returns metadata about the API, Swagger docs URL, and Prometheus metrics URL."
)
def read_root():
    return {
        "app": "OCI Always Free Monitor API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_v1": "/api/v1/summary",
        "metrics_url": "/metrics",
    }
