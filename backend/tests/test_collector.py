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
