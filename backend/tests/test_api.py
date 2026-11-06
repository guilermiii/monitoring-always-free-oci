import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def mock_summary_data():
    return {
        "status": "healthy",
        "collected_at": "2026-11-03T18:00:00Z",
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
                "orphan_volumes_count": 1,
                "orphan_wasted_gb": 50,
                "boot_volumes_count": 2,
                "block_volumes_count": 1
            },
            "object_storage": {
                "standard_gb": 2.0,
                "limit_standard_gb": 10.0,
                "standard_percentage": 20.0,
                "archive_gb": 0.5,
                "limit_archive_gb": 10.0,
                "bucket_count": 2,
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
                "monthly_ocpu_hours": 1000.0,
                "monthly_ocpu_hours_limit": 3000.0,
                "projected_ocpu_hours": 2500.0,
                "status": "warning"
            },
            "amd_micro": {
                "active_instances": 1,
                "limit_instances": 2,
                "status": "safe"
            }
        },
        "network": {
            "egress_tb_current": 0.5,
            "egress_tb_limit": 10.0,
            "egress_projected_tb": 1.5,
            "status": "safe"
        },
        "burn_rate": {
            "days_elapsed": 5,
            "days_in_month": 30,
            "ocpu_burn_rate_daily": 50.0,
            "egress_burn_rate_daily_gb": 16.6,
            "warnings": []
        },
        "api_usage": {
            "calls_today": 48,
            "daily_limit": 10000,
            "calls_last_run": 16,
            "rate_limit_per_minute": 3000,
            "percentage": 0.48,
            "status": "safe"
        }
    }


@pytest.fixture
def mock_volumes_data():
    return [
        {
            "id": "ocid1.bootvolume.oc1..bv1",
            "display_name": "boot-vm-prod",
            "volume_type": "boot",
            "size_in_gbs": 50,
            "compartment_name": "root",
            "is_orphan": False,
            "attached_instance_id": "ocid1.instance.oc1..inst1",
            "time_created": "2026-01-01T00:00:00Z"
        },
        {
            "id": "ocid1.bootvolume.oc1..bv2_orphan",
            "display_name": "boot-old-vm",
            "volume_type": "boot",
            "size_in_gbs": 50,
            "compartment_name": "dev",
            "is_orphan": True,
            "attached_instance_id": None,
            "time_created": "2026-02-01T00:00:00Z"
        }
    ]


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Test GET /api/v1/health returns 200 OK and status."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded", "healthy"]


@pytest.mark.asyncio
async def test_get_summary_from_cache(mock_redis, mock_summary_data):
    """Test GET /api/v1/summary retrieves pre-cached JSON in <5ms without calling OCI APIs."""
    from app.main import app

    # Prepopulate cache
    await mock_redis.set("oci:free_tier:summary", json.dumps(mock_summary_data))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/summary")
            assert response.status_code == 200
            data = response.json()
            assert data["storage"]["block_storage"]["total_allocated_gb"] == 150
            assert data["compute"]["ampere_a1"]["ocpus_allocated"] == 4.0


@pytest.mark.asyncio
async def test_post_refresh_triggers_collector(mock_redis, mock_summary_data):
    """Test POST /api/v1/refresh rejects anonymous requests with 401 and accepts admin with 200."""
    from app.main import app
    from app.services.security import create_access_token

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.services.worker.collect_and_cache", AsyncMock(return_value=mock_summary_data)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Anonymous request should be blocked
                unauth_resp = await ac.post("/api/v1/refresh")
                assert unauth_resp.status_code == 401
                assert "Autenticação administrativa necessária" in unauth_resp.json()["detail"]

                # 2. Authenticated admin request should succeed
                token = create_access_token({"sub": "admin"})
                auth_resp = await ac.post("/api/v1/refresh", headers={"Authorization": f"Bearer {token}"})
                assert auth_resp.status_code == 200
                data = auth_resp.json()
                assert data["status"] == "healthy"
                assert data["storage"]["block_storage"]["orphan_volumes_count"] == 1


@pytest.mark.asyncio
async def test_get_storage_volumes_endpoint(mock_redis, mock_volumes_data):
    """Test GET /api/v1/storage/volumes masks for visitors and unmasks for admin."""
    from app.main import app
    from app.services.security import create_access_token

    await mock_redis.set("oci:free_tier:volumes", json.dumps(mock_volumes_data))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Anonymous visitor gets masked data
            guest_resp = await ac.get("/api/v1/storage/volumes")
            assert guest_resp.status_code == 200
            guest_data = guest_resp.json()
            assert len(guest_data) == 2
            guest_orphans = [v for v in guest_data if v["is_orphan"]]
            assert len(guest_orphans) == 1
            assert "..." in guest_orphans[0]["id"]
            assert guest_orphans[0]["id"].endswith("phan")

            # 2. Admin gets unmasked original data
            token = create_access_token({"sub": "admin"})
            admin_resp = await ac.get("/api/v1/storage/volumes", headers={"Authorization": f"Bearer {token}"})
            assert admin_resp.status_code == 200
            admin_data = admin_resp.json()
            admin_orphans = [v for v in admin_data if v["is_orphan"]]
            assert admin_orphans[0]["id"] == "ocid1.bootvolume.oc1..bv2_orphan"


@pytest.mark.asyncio
async def test_get_network_inventory_endpoint(mock_redis):
    """Test GET /api/v1/network/inventory masks for visitors and unmasks for admin."""
    from app.main import app
    from app.services.security import create_access_token

    sample_net = {
        "vcns": [{"id": "vcn1", "display_name": "prod-vcn", "cidr_block": "10.0.0.0/16"}],
        "public_ips": [{"id": "ip1", "ip_address": "129.148.1.10", "is_unassigned": False}],
        "unassigned_ips": [],
        "load_balancers": [{"id": "lb1", "display_name": "web-alb", "lb_type": "flexible"}],
    }
    await mock_redis.set("oci:free_tier:network", json.dumps(sample_net))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Guest check (masked)
            guest_resp = await ac.get("/api/v1/network/inventory")
            assert guest_resp.status_code == 200
            guest_data = guest_resp.json()
            assert len(guest_data["vcns"]) == 1
            assert "***" in guest_data["vcns"][0]["display_name"]
            assert guest_data["public_ips"][0]["ip_address"] == "***.***.***.10"

            # Admin check (unmasked)
            token = create_access_token({"sub": "admin"})
            admin_resp = await ac.get("/api/v1/network/inventory", headers={"Authorization": f"Bearer {token}"})
            assert admin_resp.status_code == 200
            admin_data = admin_resp.json()
            assert admin_data["vcns"][0]["display_name"] == "prod-vcn"
            assert admin_data["public_ips"][0]["ip_address"] == "129.148.1.10"


@pytest.mark.asyncio
async def test_get_database_inventory_endpoint(mock_redis):
    """Test GET /api/v1/database/inventory masks for visitors and unmasks for admin."""
    from app.main import app
    from app.services.security import create_access_token

    sample_dbs = [
        {"id": "db1", "display_name": "app-db", "db_name": "appdb", "is_free_tier": True, "cpu_core_count": 1, "data_storage_size_in_gbs": 20, "db_workload": "OLTP", "lifecycle_state": "AVAILABLE"}
    ]
    await mock_redis.set("oci:free_tier:database", json.dumps(sample_dbs))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Guest check
            guest_resp = await ac.get("/api/v1/database/inventory")
            assert guest_resp.status_code == 200
            guest_data = guest_resp.json()
            assert len(guest_data) == 1
            assert "***" in guest_data[0]["db_name"]

            # Admin check
            token = create_access_token({"sub": "admin"})
            admin_resp = await ac.get("/api/v1/database/inventory", headers={"Authorization": f"Bearer {token}"})
            assert admin_resp.status_code == 200
            admin_data = admin_resp.json()
            assert admin_data[0]["db_name"] == "appdb"


@pytest.mark.asyncio
async def test_summary_schema_includes_api_usage(mock_redis, mock_summary_data):
    """Test GET /api/v1/summary properly serializes api_usage field."""
    from app.main import app

    mock_summary_data["api_usage"] = {
        "calls_today": 120,
        "daily_limit": 10000,
        "calls_last_run": 15,
        "rate_limit_per_minute": 3000,
        "percentage": 1.2,
        "status": "safe"
    }
    await mock_redis.set("oci:free_tier:summary", json.dumps(mock_summary_data))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/summary")
            assert response.status_code == 200
            data = response.json()
            assert "api_usage" in data
            assert data["api_usage"]["calls_today"] == 120
            assert data["api_usage"]["daily_limit"] == 10000
            assert data["api_usage"]["calls_last_run"] == 15
            assert data["api_usage"]["rate_limit_per_minute"] == 3000
            assert data["api_usage"]["percentage"] == 1.2
            assert data["api_usage"]["status"] == "safe"


@pytest.mark.asyncio
async def test_summary_includes_networking_with_both_ip_types(mock_redis, mock_summary_data):
    """Test GET /api/v1/summary properly serializes networking.public_ip with reserved and ephemeral counts."""
    from app.main import app

    mock_summary_data["networking"] = {
        "vcn": {"active_vcns": 1, "limit_vcns": 2, "percentage": 50.0, "status": "safe"},
        "public_ip": {
            "reserved_count": 1,
            "reserved_limit": 1,
            "unassigned_reserved_count": 0,
            "ephemeral_count": 2,
            "total_active_ips": 3,
            "percentage": 100.0,
            "status": "warning"
        },
        "load_balancer": {"flexible_lb_count": 1, "limit_flexible_lb": 1, "nlb_count": 0, "limit_nlb": 1, "status": "safe"},
        "bastion": {"active_bastions": 1, "limit_bastions": 2, "status": "safe"},
        "egress": {"egress_tb_current": 0.5, "egress_tb_limit": 10.0, "egress_projected_tb": 1.5, "status": "safe"}
    }
    await mock_redis.set("oci:free_tier:summary", json.dumps(mock_summary_data))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/summary")
            assert response.status_code == 200
            data = response.json()
            assert "networking" in data
            pip = data["networking"]["public_ip"]
            assert pip["reserved_count"] == 1
            assert pip["ephemeral_count"] == 2
            assert pip["total_active_ips"] == 3
            assert pip["status"] == "warning"


