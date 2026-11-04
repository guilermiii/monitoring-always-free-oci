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
