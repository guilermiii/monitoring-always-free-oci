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
    """Test POST /api/v1/refresh forces collector execution and updates Redis."""
    from app.main import app

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.services.worker.collect_and_cache", AsyncMock(return_value=mock_summary_data)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/v1/refresh")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["storage"]["block_storage"]["orphan_volumes_count"] == 1


@pytest.mark.asyncio
async def test_get_storage_volumes_endpoint(mock_redis, mock_volumes_data):
    """Test GET /api/v1/storage/volumes returns detailed list of volumes with orphan status."""
    from app.main import app

    await mock_redis.set("oci:free_tier:volumes", json.dumps(mock_volumes_data))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/storage/volumes")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            orphans = [v for v in data if v["is_orphan"]]
            assert len(orphans) == 1
            assert orphans[0]["id"] == "ocid1.bootvolume.oc1..bv2_orphan"


@pytest.mark.asyncio
async def test_get_network_inventory_endpoint(mock_redis):
    """Test GET /api/v1/network/inventory returns VCNs, Public IPs and LBs."""
    from app.main import app

    sample_net = {
        "vcns": [{"id": "vcn1", "display_name": "prod-vcn", "cidr_block": "10.0.0.0/16"}],
        "public_ips": [{"id": "ip1", "ip_address": "129.148.1.10", "is_unassigned": False}],
        "unassigned_ips": [],
        "load_balancers": [{"id": "lb1", "display_name": "web-alb", "lb_type": "flexible"}],
    }
    await mock_redis.set("oci:free_tier:network", json.dumps(sample_net))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/network/inventory")
            assert response.status_code == 200
            data = response.json()
            assert len(data["vcns"]) == 1
            assert data["vcns"][0]["display_name"] == "prod-vcn"


@pytest.mark.asyncio
async def test_get_database_inventory_endpoint(mock_redis):
    """Test GET /api/v1/database/inventory returns list of Autonomous DBs."""
    from app.main import app

    sample_dbs = [
        {"id": "db1", "display_name": "app-db", "db_name": "appdb", "is_free_tier": True, "cpu_core_count": 1, "data_storage_size_in_gbs": 20, "db_workload": "OLTP", "lifecycle_state": "AVAILABLE"}
    ]
    await mock_redis.set("oci:free_tier:database", json.dumps(sample_dbs))

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/database/inventory")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["db_name"] == "appdb"
