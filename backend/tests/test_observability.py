import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.routers.observability import set_app_started


@pytest.fixture
def mock_summary_data():
    return {
        "status": "healthy",
        "collected_at": "2026-11-05T12:00:00Z",
        "tenancy": {
            "id": "ocid1.tenancy.oc1..root",
            "name": "my-tenancy",
            "home_region": "us-ashburn-1"
        },
        "storage": {
            "block_storage": {
                "total_allocated_gb": 150,
                "limit_gb": 200,
                "percentage": 75.0,
                "status": "warning",
                "orphan_volumes_count": 2,
                "orphan_wasted_gb": 80,
                "boot_volumes_count": 2,
                "block_volumes_count": 1
            },
            "object_storage": {
                "standard_gb": 3.5,
                "limit_standard_gb": 10.0,
                "standard_percentage": 35.0,
                "archive_gb": 1.0,
                "limit_archive_gb": 10.0,
                "bucket_count": 3,
                "status": "safe"
            }
        },
        "compute": {
            "ampere_a1": {
                "ocpus_allocated": 4.0,
                "limit_ocpus": 4.0,
                "memory_gb_allocated": 24.0,
                "limit_memory_gb": 24.0,
                "instances_count": 2,
                "monthly_ocpu_hours": 1200.0,
                "monthly_ocpu_hours_limit": 3000.0,
                "projected_ocpu_hours": 2800.0,
                "status": "warning"
            },
            "amd_micro": {
                "active_instances": 1,
                "limit_instances": 2,
                "status": "safe"
            }
        },
        "networking": {
            "vcn": {"active_vcns": 1, "limit_vcns": 2, "percentage": 50.0, "status": "safe"},
            "public_ip": {
                "reserved_count": 1,
                "reserved_limit": 1,
                "unassigned_reserved_count": 1,
                "ephemeral_count": 2,
                "total_active_ips": 3,
                "percentage": 100.0,
                "status": "warning"
            },
            "load_balancer": {"flexible_lb_count": 1, "limit_flexible_lb": 1, "nlb_count": 0, "limit_nlb": 1, "status": "safe"},
            "bastion": {"active_bastions": 1, "limit_bastions": 2, "status": "safe"},
            "egress": {"egress_tb_current": 0.5, "egress_tb_limit": 10.0, "egress_projected_tb": 1.5, "status": "safe"}
        },
        "network": {
            "egress_tb_current": 0.5,
            "egress_tb_limit": 10.0,
            "egress_projected_tb": 1.5,
            "status": "safe"
        },
        "database": {
            "autonomous_database": {
                "active_count": 1,
                "limit_count": 2,
                "allocated_storage_gb": 20.0,
                "limit_storage_gb": 40.0,
                "percentage": 50.0,
                "status": "safe"
            }
        },
        "burn_rate": {
            "days_elapsed": 5,
            "days_in_month": 30,
            "ocpu_burn_rate_daily": 50.0,
            "egress_burn_rate_daily_gb": 16.6,
            "warnings": []
        },
        "api_usage": {
            "calls_today": 75,
            "daily_limit": 10000,
            "calls_last_run": 15,
            "rate_limit_per_minute": 3000,
            "percentage": 0.75,
            "status": "safe"
        }
    }


@pytest.mark.asyncio
async def test_liveness_probe_returns_200():
    """Verify that GET /livez returns 200 OK and status 'alive'."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/livez")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_healthy(mock_redis):
    """Verify that GET /readyz returns 200 OK when Redis and OCI config are healthy."""
    from app.main import app

    mock_oci_cfg = {"tenancy": "ocid1.tenancy...", "key_file": "/path/to/key.pem"}
    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.routers.observability.load_oci_config", return_value=mock_oci_cfg):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/readyz")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ready"
                assert data["redis_connected"] is True
                assert data["oci_configured"] is True


@pytest.mark.asyncio
async def test_readiness_probe_unhealthy_when_redis_down():
    """Verify that GET /readyz returns 503 when Redis ping fails."""
    from app.main import app

    mock_oci_cfg = {"tenancy": "ocid1.tenancy...", "key_file": "/path/to/key.pem"}
    with patch("app.services.cache.ping_redis", AsyncMock(return_value=False)):
        with patch("app.routers.observability.load_oci_config", return_value=mock_oci_cfg):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/readyz")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "not_ready"
                assert data["redis_connected"] is False
                assert "Redis" in data["details"]


@pytest.mark.asyncio
async def test_readiness_probe_unhealthy_when_oci_misconfigured(mock_redis):
    """Verify that GET /readyz returns 503 when OCI credentials cannot be loaded."""
    from app.main import app

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.routers.observability.load_oci_config", side_effect=Exception("Missing config")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/readyz")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "not_ready"
                assert data["oci_configured"] is False
                assert "OCI config load error" in data["details"]


@pytest.mark.asyncio
async def test_startup_probe_lifecycle():
    """Verify GET /startupz returns 200 when started, and 503 when starting."""
    from app.main import app

    set_app_started(True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/startupz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["app_started"] is True

    set_app_started(False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/startupz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "starting"
        assert data["app_started"] is False

    # Restore healthy state
    set_app_started(True)


@pytest.mark.asyncio
async def test_healthz_endpoint(mock_redis):
    """Verify GET /healthz returns 200 or 503 matching dependencies."""
    from app.main import app

    mock_oci_cfg = {"tenancy": "ocid1.tenancy...", "key_file": "/path/to/key.pem"}
    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.routers.observability.load_oci_config", return_value=mock_oci_cfg):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/healthz")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    """Verify GET /metrics returns Prometheus text format (version 0.0.4)."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Trigger an API call first to increment HTTP metrics
        await ac.get("/livez")

        response = await ac.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        body = response.text
        assert "http_requests_total" in body
        assert "http_request_duration_seconds" in body
        assert "oci_storage_block_limit_gb" in body


@pytest.mark.asyncio
async def test_prometheus_oci_gauges_populated_from_cache(mock_redis, mock_summary_data):
    """Verify that scraping /metrics refreshes OCI gauges from Redis summary cache."""
    from app.main import app

    await mock_redis.set("oci:free_tier:summary", json.dumps(mock_summary_data))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/metrics")
            assert response.status_code == 200
            body = response.text
            assert "oci_storage_block_allocated_gb 150.0" in body
            assert "oci_storage_orphan_volumes_count 2.0" in body
            assert "oci_storage_orphan_wasted_gb 80.0" in body
            assert "oci_compute_ampere_ocpus_allocated 4.0" in body
            assert "oci_network_vcns_count 1.0" in body
            assert "oci_network_unassigned_ips_count 1.0" in body
            assert "oci_database_autonomous_count 1.0" in body
            assert "oci_api_calls_today 75.0" in body


@pytest.mark.asyncio
async def test_root_endpoint_metadata():
    """Verify GET / returns RootResponse with metrics_url and docs_url."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "OCI Always Free Monitor API"
        assert data["docs_url"] == "/docs"
        assert data["metrics_url"] == "/metrics"


@pytest.mark.asyncio
async def test_openapi_swagger_schema_includes_probes_and_metrics():
    """Verify OpenAPI JSON schema includes probes, metrics, and typed response schemas."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

        paths = schema["paths"]
        assert "/metrics" in paths
        assert "/livez" in paths
        assert "/readyz" in paths
        assert "/startupz" in paths
        assert "/healthz" in paths
        assert "/api/v1/network/inventory" in paths
        assert "/api/v1/database/inventory" in paths

        # Verify probe error responses are documented in OpenAPI
        readyz_responses = paths["/readyz"]["get"]["responses"]
        assert "200" in readyz_responses
        assert "503" in readyz_responses

        startupz_responses = paths["/startupz"]["get"]["responses"]
        assert "200" in startupz_responses
        assert "503" in startupz_responses

        # Verify NetworkInventoryResponse schema
        components = schema["components"]["schemas"]
        assert "NetworkInventoryResponse" in components
        assert "LivenessResponse" in components
        assert "ReadinessResponse" in components
        assert "StartupResponse" in components
        assert "RootResponse" in components
