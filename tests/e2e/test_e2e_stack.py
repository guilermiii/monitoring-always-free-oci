"""
End-to-End (E2E) Integration Tests for OCI Always Free Monitor.
Executes against the running containers (via docker-compose).
"""
import os
import pytest
import httpx

FRONTEND_URL = os.getenv("E2E_FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("E2E_BACKEND_URL", "http://localhost:8000")


@pytest.mark.asyncio
async def test_e2e_frontend_serves_spa():
    """Verify that Nginx frontend serves the SPA index.html on port 3000."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(FRONTEND_URL)
            assert response.status_code == 200
            assert "<!doctype html>" in response.text.lower() or "<html" in response.text.lower()
            assert "OCI Always Free" in response.text or "root" in response.text
        except httpx.ConnectError:
            pytest.skip(f"Frontend not running at {FRONTEND_URL} (skip unless stack is up)")


@pytest.mark.asyncio
async def test_e2e_reverse_proxy_health():
    """Verify that Nginx proxies /api/v1/health correctly to FastAPI."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{FRONTEND_URL}/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
        except httpx.ConnectError:
            pytest.skip(f"Frontend proxy not reachable at {FRONTEND_URL}")


@pytest.mark.asyncio
async def test_e2e_backend_direct_summary():
    """Verify direct backend summary endpoint on port 8000."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/summary")
            assert response.status_code in [200, 503]
            if response.status_code == 200:
                data = response.json()
                assert "storage" in data
                assert "compute" in data
                assert "networking" in data
                assert "database" in data
                assert "burn_rate" in data
                if "api_usage" in data and data["api_usage"] is not None:
                    assert "calls_today" in data["api_usage"]
                    assert "daily_limit" in data["api_usage"]
                    assert data["api_usage"]["daily_limit"] >= 1000
        except httpx.ConnectError:
            pytest.skip(f"Backend not reachable at {BACKEND_URL}")


@pytest.mark.asyncio
async def test_e2e_network_and_database_inventory():
    """Verify proxy routing for network and database inventory endpoints."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            net_resp = await client.get(f"{FRONTEND_URL}/api/v1/network/inventory")
            assert net_resp.status_code in [200, 503]
            if net_resp.status_code == 200:
                net_data = net_resp.json()
                assert "vcns" in net_data
                assert "public_ips" in net_data
                assert "load_balancers" in net_data

            db_resp = await client.get(f"{FRONTEND_URL}/api/v1/database/inventory")
            assert db_resp.status_code in [200, 503]
        except httpx.ConnectError:
            pytest.skip(f"Frontend proxy not reachable at {FRONTEND_URL}")


@pytest.mark.asyncio
async def test_e2e_kubernetes_probes():
    """Verify Kubernetes probes (livez, readyz, startupz) on both backend and frontend proxy."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Backend direct checks
            live_resp = await client.get(f"{BACKEND_URL}/livez")
            assert live_resp.status_code == 200
            assert live_resp.json()["status"] == "alive"

            ready_resp = await client.get(f"{BACKEND_URL}/readyz")
            assert ready_resp.status_code in [200, 503]

            startup_resp = await client.get(f"{BACKEND_URL}/startupz")
            assert startup_resp.status_code in [200, 503]

            # Frontend proxy checks
            fe_live = await client.get(f"{FRONTEND_URL}/livez")
            assert fe_live.status_code == 200
            assert fe_live.json()["status"] == "alive"
        except httpx.ConnectError:
            pytest.skip("Stack not running for E2E probe validation")


@pytest.mark.asyncio
async def test_e2e_prometheus_metrics():
    """Verify Prometheus metrics scrape endpoint returns text/plain format."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{BACKEND_URL}/metrics")
            assert resp.status_code == 200
            assert "text/plain" in resp.headers["content-type"]
            assert "http_requests_total" in resp.text
            assert "oci_storage_block_limit_gb" in resp.text

            # Test via frontend proxy
            fe_resp = await client.get(f"{FRONTEND_URL}/metrics")
            assert fe_resp.status_code == 200
            assert "text/plain" in fe_resp.headers["content-type"]
        except httpx.ConnectError:
            pytest.skip("Stack not running for E2E metrics validation")


@pytest.mark.asyncio
async def test_e2e_swagger_and_openapi():
    """Verify Swagger UI and OpenAPI schema completeness."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{BACKEND_URL}/openapi.json")
            assert resp.status_code == 200
            data = resp.json()
            assert "/metrics" in data["paths"]
            assert "/livez" in data["paths"]
            assert "/readyz" in data["paths"]
            assert "/startupz" in data["paths"]
        except httpx.ConnectError:
            pytest.skip("Backend not running for OpenAPI validation")

