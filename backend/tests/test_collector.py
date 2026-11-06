import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


def test_collect_active_compartments(sample_compartments):
    """Test recursive filtering of active compartments starting from root."""
    from app.services.oci_collector import filter_active_compartments

    active = filter_active_compartments(sample_compartments)
    ids = [c.id for c in active]
    assert "ocid1.tenancy.oc1..root" in ids
    assert "ocid1.compartment.oc1..dev" in ids
    assert "ocid1.compartment.oc1..deleted" not in ids


def test_block_storage_and_orphan_detection(sample_volumes_and_attachments):
    """
    Test summing total storage and identifying orphan boot/block volumes.
    Sample data has:
    - 2 boot volumes of 50 GB (1 attached, 1 orphan)
    - 2 block volumes of 50 GB (1 attached, 1 orphan)
    Total = 200 GB
    Orphans = 2 volumes, 100 GB wasted.
    """
    from app.services.oci_collector import process_block_storage_inventory

    result = process_block_storage_inventory(
        boot_volumes=sample_volumes_and_attachments["boot_volumes"],
        block_volumes=sample_volumes_and_attachments["block_volumes"],
        boot_attachments=sample_volumes_and_attachments["boot_attachments"],
        volume_attachments=sample_volumes_and_attachments["volume_attachments"],
    )

    assert result["total_allocated_gb"] == 200
    assert result["limit_gb"] == 200
    assert result["percentage"] == 100.0
    assert result["orphan_volumes_count"] == 2
    assert result["orphan_wasted_gb"] == 100
    assert result["status"] == "danger"  # >= 90%
    assert len(result["orphan_volumes"]) == 2

    # Check details of orphan items
    orphan_ids = [v["id"] for v in result["orphan_volumes"]]
    assert "ocid1.bootvolume.oc1..bv2_orphan" in orphan_ids
    assert "ocid1.volume.oc1..blk2_orphan" in orphan_ids


def test_terminated_volumes_are_ignored_and_not_marked_orphan():
    """
    Test that volumes with lifecycle_state == 'TERMINATED' or 'TERMINATING'
    are completely excluded from quota calculation and never marked as orphan disks.
    """
    from app.services.oci_collector import process_block_storage_inventory

    # 1 Available attached boot volume (50 GB)
    bv_active = MagicMock(id="bv_act", size_in_gbs=50, lifecycle_state="AVAILABLE", display_name="active-bv")
    # 2 Terminated boot volumes (50 GB each)
    bv_term1 = MagicMock(id="bv_term1", size_in_gbs=50, lifecycle_state="TERMINATED", display_name="terminated-bv1")
    bv_term2 = MagicMock(id="bv_term2", size_in_gbs=50, lifecycle_state="TERMINATING", display_name="terminating-bv2")

    # 1 Available detached block volume (50 GB) -> REAL ORPHAN
    blk_orphan = MagicMock(id="blk_orph", size_in_gbs=50, lifecycle_state="AVAILABLE", display_name="orphan-blk")
    # 1 Terminated block volume (50 GB)
    blk_term = MagicMock(id="blk_term", size_in_gbs=50, lifecycle_state="TERMINATED", display_name="terminated-blk")

    # Attachment for active boot volume
    att = MagicMock(boot_volume_id="bv_act", lifecycle_state="ATTACHED", instance_id="inst1")

    result = process_block_storage_inventory(
        boot_volumes=[bv_active, bv_term1, bv_term2],
        block_volumes=[blk_orphan, blk_term],
        boot_attachments=[att],
        volume_attachments=[],
    )

    # Only active volumes should be counted: bv_active (50 GB) + blk_orphan (50 GB) = 100 GB
    assert result["total_allocated_gb"] == 100
    assert result["boot_volumes_count"] == 1
    assert result["block_volumes_count"] == 1
    # Only 1 orphan disk (blk_orphan)
    assert result["orphan_volumes_count"] == 1
    assert result["orphan_wasted_gb"] == 50
    orphan_ids = [v["id"] for v in result["orphan_volumes"]]
    assert orphan_ids == ["blk_orph"]
    assert "bv_term1" not in orphan_ids
    assert "bv_term2" not in orphan_ids
    assert "blk_term" not in orphan_ids


def test_compute_instances_aggregation(sample_compute_instances):
    """
    Test compute aggregation for Ampere A1 (Arm) and AMD Micro.
    Sample data:
    - 2x Ampere A1 with 2 OCPUs and 12 GB RAM each -> 4 OCPUs, 24 GB RAM.
    - 1x AMD Micro RUNNING.
    - 1x AMD Micro TERMINATED (ignored).
    """
    from app.services.oci_collector import process_compute_inventory

    result = process_compute_inventory(sample_compute_instances)

    # Ampere A1
    ampere = result["ampere_a1"]
    assert ampere["ocpus_allocated"] == 4.0
    assert ampere["limit_ocpus"] == 4.0
    assert ampere["memory_gb_allocated"] == 24.0
    assert ampere["limit_memory_gb"] == 24.0
    assert ampere["instances_count"] == 2

    # AMD Micro
    micro = result["amd_micro"]
    assert micro["active_instances"] == 1
    assert micro["limit_instances"] == 2
    assert micro["status"] == "safe"


def test_compute_instances_inventory_details(sample_compute_instances):
    """
    Test that process_compute_inventory extracts the detailed instance inventory
    with columns in order: nome, arquitetura, cpu, memoria, compartment.
    Terminated instances must be excluded.
    """
    from app.services.oci_collector import process_compute_inventory

    comp_map = {
        "ocid1.tenancy.oc1..root": "root",
        "ocid1.compartment.oc1..dev": "dev-team"
    }

    result = process_compute_inventory(sample_compute_instances, compartment_map=comp_map)
    assert "instances_detail" in result
    details = result["instances_detail"]

    # 3 running instances (2 Ampere, 1 Micro), 1 terminated instance ignored
    assert len(details) == 3

    # Check Ampere instance 1
    arm1 = next(i for i in details if i["display_name"] == "arm-app-server")
    assert arm1["architecture"] == "ARM (Ampere A1 Flex)"
    assert arm1["ocpus"] == 2.0
    assert arm1["memory_gb"] == 12.0
    assert arm1["compartment_name"] == "root"
    assert arm1["lifecycle_state"] == "RUNNING"

    # Check Ampere instance 2 in dev compartment
    arm2 = next(i for i in details if i["display_name"] == "arm-db-server")
    assert arm2["architecture"] == "ARM (Ampere A1 Flex)"
    assert arm2["ocpus"] == 2.0
    assert arm2["memory_gb"] == 12.0
    assert arm2["compartment_name"] == "dev-team"

    # Check Micro instance
    micro = next(i for i in details if i["display_name"] == "micro-vpn")
    assert micro["architecture"] == "AMD (Micro)"
    assert micro["ocpus"] == 1.0
    assert micro["memory_gb"] == 1.0
    assert micro["compartment_name"] == "root"



def test_object_storage_aggregation(sample_object_storage):
    """Test object storage bytes to GB conversion and tier aggregation."""
    from app.services.oci_collector import process_object_storage_inventory

    result = process_object_storage_inventory(
        buckets=sample_object_storage["buckets"]
    )

    assert pytest.approx(result["standard_gb"], 0.1) == 3.0
    assert pytest.approx(result["archive_gb"], 0.1) == 1.0
    assert result["bucket_count"] == 2
    assert result["limit_standard_gb"] == 10.0
    assert result["standard_percentage"] == 30.0
    assert result["status"] == "safe"


def test_burn_rate_calculation():
    """Test daily burn rate and end-of-month projection."""
    from app.services.oci_collector import calculate_burn_rate_projection

    # 10 days elapsed in a 30-day month
    # Consumed 1,000 OCPU-hours so far
    # Daily burn rate = 100 OCPU-hours/day
    # Projected = 3,000 OCPU-hours (At the 3,000 limit)
    res = calculate_burn_rate_projection(
        current_ocpu_hours=1000.0,
        current_egress_gb=3000.0,  # ~3 TB
        days_elapsed=10,
        days_in_month=30
    )

    assert res["days_elapsed"] == 10
    assert res["days_in_month"] == 30
    assert res["ocpu_burn_rate_daily"] == 100.0
    assert res["projected_ocpu_hours"] == 3000.0
    assert pytest.approx(res["egress_burn_rate_daily_gb"], 0.1) == 300.0
    assert pytest.approx(res["projected_egress_gb"], 0.1) == 9000.0  # 9 TB / 10 TB


def test_burn_rate_warning_on_exceeding():
    """Test that burn-rate generates alerts when projected usage exceeds 100%."""
    from app.services.oci_collector import calculate_burn_rate_projection

    # 10 days elapsed, 1,200 OCPU-hours -> 120/day -> 3,600 projected (> 3,000)
    res = calculate_burn_rate_projection(
        current_ocpu_hours=1200.0,
        current_egress_gb=11000.0,  # 11 TB projected > 10 TB limit
        days_elapsed=10,
        days_in_month=30
    )

    assert res["projected_ocpu_hours"] == 3600.0
    assert len(res["warnings"]) >= 1
    assert any("OCPU" in w for w in res["warnings"])


def test_vcn_aggregation_and_filtering(sample_vcns):
    """Test counting active VCNs and ignoring terminated ones."""
    from app.services.oci_collector import process_vcn_inventory

    result = process_vcn_inventory(sample_vcns)
    assert result["active_vcns"] == 1
    assert result["limit_vcns"] == 2
    assert result["percentage"] == 50.0
    assert result["status"] == "safe"
    assert len(result["vcns_detail"]) == 1
    assert result["vcns_detail"][0]["id"] == "ocid1.vcn.oc1..vcn1"


def test_public_ip_aggregation_and_unassigned_detection(sample_public_ips):
    """
    Test categorizing reserved vs ephemeral public IPs,
    and detecting unassigned (orphan) reserved IPs.
    """
    from app.services.oci_collector import process_public_ip_inventory

    result = process_public_ip_inventory(sample_public_ips)
    assert result["reserved_count"] == 2
    assert result["reserved_limit"] == 1
    assert result["unassigned_reserved_count"] == 1
    assert result["ephemeral_count"] == 1
    assert result["total_active_ips"] == 3
    # 2 reserved > 1 limit -> danger
    assert result["status"] == "danger"
    assert len(result["unassigned_ips"]) == 1
    assert result["unassigned_ips"][0]["ip_address"] == "129.148.1.20"


def test_public_ip_with_assigned_state_and_private_ip():
    """
    Verify that public IPs with lifecycle_state='ASSIGNED' (e.g., attached to a PRIVATE_IP or NAT_GATEWAY)
    are correctly counted and not discarded by the collector.
    """
    from app.services.oci_collector import process_public_ip_inventory
    from unittest.mock import MagicMock

    # 1. Reserved IP attached to a Private IP (ASSIGNED lifecycle state)
    ip_reserved_assigned = MagicMock()
    ip_reserved_assigned.id = "ocid1.publicip.oc1..pip_fixed"
    ip_reserved_assigned.ip_address = "137.131.207.152"
    ip_reserved_assigned.display_name = "pip-blog-do-zeca-fixed"
    ip_reserved_assigned.lifetime = "RESERVED"
    ip_reserved_assigned.lifecycle_state = "ASSIGNED"
    ip_reserved_assigned.assigned_entity_id = "ocid1.privateip.oc1..priv1"
    ip_reserved_assigned.assigned_entity_type = "PRIVATE_IP"
    ip_reserved_assigned.compartment_id = "ocid1.compartment.oc1..c1"

    # 2. Ephemeral IP assigned to a NAT Gateway (ASSIGNED lifecycle state)
    ip_eph_assigned = MagicMock()
    ip_eph_assigned.id = "ocid1.publicip.oc1..pip_nat"
    ip_eph_assigned.ip_address = "163.176.85.210"
    ip_eph_assigned.display_name = "IP for NAT gateway"
    ip_eph_assigned.lifetime = "EPHEMERAL"
    ip_eph_assigned.lifecycle_state = "ASSIGNED"
    ip_eph_assigned.assigned_entity_id = "ocid1.natgateway.oc1..nat1"
    ip_eph_assigned.assigned_entity_type = "NAT_GATEWAY"
    ip_eph_assigned.compartment_id = "ocid1.compartment.oc1..c1"

    # 3. Terminated IP (should be ignored)
    ip_terminated = MagicMock()
    ip_terminated.id = "ocid1.publicip.oc1..pip_dead"
    ip_terminated.ip_address = "137.131.207.99"
    ip_terminated.display_name = "terminated"
    ip_terminated.lifetime = "RESERVED"
    ip_terminated.lifecycle_state = "TERMINATED"
    ip_terminated.assigned_entity_id = None

    raw_ips = [ip_reserved_assigned, ip_eph_assigned, ip_terminated]
    comp_map = {"ocid1.compartment.oc1..c1": "pipeline-terraform"}

    result = process_public_ip_inventory(raw_ips, comp_map)

    assert result["reserved_count"] == 1
    assert result["reserved_limit"] == 1
    assert result["unassigned_reserved_count"] == 0
    assert result["ephemeral_count"] == 1
    assert result["total_active_ips"] == 2
    assert result["percentage"] == 100.0
    assert result["status"] == "danger"
    assert len(result["unassigned_ips"]) == 0
    assert len(result["all_ips"]) == 2

    # Check details of reserved IP
    res_ip = next(ip for ip in result["all_ips"] if ip["lifetime"] == "RESERVED")
    assert res_ip["ip_address"] == "137.131.207.152"
    assert res_ip["is_unassigned"] is False
    assert res_ip["assigned_entity_type"] == "PRIVATE_IP"
    assert res_ip["compartment_name"] == "pipeline-terraform"



def test_load_balancer_aggregation(sample_load_balancers):
    """Test counting active flexible load balancers and NLBs."""
    from app.services.oci_collector import process_load_balancer_inventory

    result = process_load_balancer_inventory(
        lbs=sample_load_balancers["load_balancers"],
        nlbs=sample_load_balancers["network_load_balancers"],
    )

    assert result["flexible_lb_count"] == 1
    assert result["limit_flexible_lb"] == 1
    assert result["nlb_count"] == 1
    assert result["limit_nlb"] == 1
    assert result["status"] == "danger"  # at 100% capacity


def test_autonomous_database_aggregation(sample_autonomous_databases):
    """Test counting active Always Free autonomous databases and storage."""
    from app.services.oci_collector import process_autonomous_database_inventory

    result = process_autonomous_database_inventory(sample_autonomous_databases)
    assert result["active_count"] == 1
    assert result["limit_count"] == 2
    assert result["allocated_storage_gb"] == 20.0
    assert result["limit_storage_gb"] == 40.0
    assert result["status"] == "safe"
    assert len(result["databases_detail"]) == 1
    assert result["databases_detail"][0]["db_name"] == "appdb"


def test_bastion_aggregation(sample_bastions):
    """Test counting active bastions and ignoring deleted ones."""
    from app.services.oci_collector import process_bastion_inventory

    result = process_bastion_inventory(sample_bastions)
    assert result["active_bastions"] == 1
    assert result["limit_bastions"] == 2
    assert result["status"] == "safe"


def test_collector_tracks_api_calls_count():
    """Test that OCICollector initializes and tracks API calls count."""
    from app.services.oci_collector import OCICollector

    collector = OCICollector(config_dict={"tenancy": "ocid1.tenancy.oc1..test", "region": "sa-saopaulo-1"})
    assert collector.api_calls_count == 0

    collector._track_call()
    assert collector.api_calls_count == 1

    collector._track_call(4)
    assert collector.api_calls_count == 5


@pytest.mark.asyncio
async def test_cache_records_api_calls(mock_redis):
    """Test recording and retrieving daily API calls in cache."""
    from app.services import cache
    from unittest.mock import patch

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        usage = await cache.record_api_calls(15)
        assert usage["calls_today"] == 15
        assert usage["calls_last_run"] == 15
        assert usage["daily_limit"] == 10000
        assert usage["rate_limit_per_minute"] == 3000
        assert usage["percentage"] == 0.15
        assert usage["status"] == "safe"

        # Record another run
        usage2 = await cache.record_api_calls(20)
        assert usage2["calls_today"] == 35
        assert usage2["calls_last_run"] == 20
        assert usage2["percentage"] == 0.35

        # Query usage directly
        cached_usage = await cache.get_api_usage()
        assert cached_usage["calls_today"] == 35
        assert cached_usage["calls_last_run"] == 20


