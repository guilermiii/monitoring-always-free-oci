import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.metrics import router as metrics_router
from app.services.worker import start_background_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("oci-monitor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background worker unless explicitly disabled (e.g. during unit tests)
    disable_worker = os.getenv("DISABLE_BACKGROUND_WORKER", "false").lower() in ["1", "true", "yes"]
    worker_task = None
    if not disable_worker:
        worker_task = asyncio.create_task(start_background_worker())
        logger.info("Background worker task created.")

    yield

    # Shutdown: Cancel worker task
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
    description="API for monitoring Oracle Cloud Infrastructure (OCI) Always Free tier resources and orphan storage.",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(metrics_router)


@app.get("/")
def read_root():
    return {
        "app": "OCI Always Free Monitor API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_v1": "/api/v1/summary",
    }
