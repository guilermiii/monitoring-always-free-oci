import time
import logging
from typing import Dict, Any, Union
from prometheus_client import (
    REGISTRY,
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

logger = logging.getLogger("oci-monitor.prometheus")

# --- HTTP Request Metrics ---
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total count of HTTP requests processed by endpoint and status code.",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Histogram of HTTP request latencies in seconds.",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# --- OCI Storage Metrics ---
OCI_STORAGE_BLOCK_ALLOCATED_GB = Gauge(
    "oci_storage_block_allocated_gb",
    "Total allocated block and boot volume storage in GB.",
)
OCI_STORAGE_BLOCK_LIMIT_GB = Gauge(
    "oci_storage_block_limit_gb",
    "OCI Always Free block storage limit in GB.",
)
OCI_STORAGE_ORPHAN_VOLUMES_COUNT = Gauge(
    "oci_storage_orphan_volumes_count",
    "Count of orphan boot and block volumes (not attached to any running instance).",
)
OCI_STORAGE_ORPHAN_WASTED_GB = Gauge(
    "oci_storage_orphan_wasted_gb",
    "Total GB of storage consumed by orphan volumes.",
)
OCI_STORAGE_OBJECT_STANDARD_GB = Gauge(
    "oci_storage_object_standard_gb",
    "Standard tier Object Storage usage in GB.",
)
OCI_STORAGE_OBJECT_ARCHIVE_GB = Gauge(
    "oci_storage_object_archive_gb",
    "Archive tier Object Storage usage in GB.",
)

# --- OCI Compute Metrics ---
OCI_COMPUTE_AMPERE_OCPUS_ALLOCATED = Gauge(
    "oci_compute_ampere_ocpus_allocated",
    "Total OCPUs allocated across Ampere A1 (Arm) instances.",
)
OCI_COMPUTE_AMPERE_OCPUS_LIMIT = Gauge(
    "oci_compute_ampere_ocpus_limit",
    "Always Free limit for Ampere A1 OCPUs.",
)
OCI_COMPUTE_AMPERE_MEMORY_GB_ALLOCATED = Gauge(
    "oci_compute_ampere_memory_gb_allocated",
    "Total memory (RAM) in GB allocated to Ampere A1 instances.",
)
OCI_COMPUTE_AMPERE_MEMORY_GB_LIMIT = Gauge(
    "oci_compute_ampere_memory_gb_limit",
    "Always Free limit for Ampere A1 memory in GB.",
)
OCI_COMPUTE_AMPERE_INSTANCES_COUNT = Gauge(
    "oci_compute_ampere_instances_count",
    "Number of active Ampere A1 flex instances.",
)
OCI_COMPUTE_AMD_MICRO_INSTANCES = Gauge(
    "oci_compute_amd_micro_instances",
    "Number of active AMD E2.1.Micro instances.",
)
OCI_COMPUTE_AMD_MICRO_LIMIT = Gauge(
    "oci_compute_amd_micro_limit",
    "Always Free limit for AMD Micro instances.",
)

# --- OCI Networking Metrics ---
OCI_NETWORK_VCNS_COUNT = Gauge(
    "oci_network_vcns_count",
    "Number of active Virtual Cloud Networks (VCNs).",
)
OCI_NETWORK_RESERVED_IPS_COUNT = Gauge(
    "oci_network_reserved_ips_count",
    "Number of reserved Public IPs in use.",
)
OCI_NETWORK_UNASSIGNED_IPS_COUNT = Gauge(
    "oci_network_unassigned_ips_count",
    "Number of unassigned (orphan) reserved Public IPs.",
)
OCI_NETWORK_EPHEMERAL_IPS_COUNT = Gauge(
    "oci_network_ephemeral_ips_count",
    "Number of active ephemeral Public IPs.",
)

# --- OCI Database Metrics ---
OCI_DATABASE_AUTONOMOUS_COUNT = Gauge(
    "oci_database_autonomous_count",
    "Number of active Always Free Autonomous Databases.",
)
OCI_DATABASE_STORAGE_GB = Gauge(
    "oci_database_storage_gb",
    "Total storage allocated to Autonomous Databases in GB.",
)

# --- OCI API Usage & Collector Status ---
OCI_API_CALLS_TODAY = Gauge(
    "oci_api_calls_today",
    "Total OCI SDK API calls executed today (UTC).",
)
OCI_API_DAILY_LIMIT = Gauge(
    "oci_api_daily_limit",
    "Configured daily limit for OCI API calls.",
)
OCI_COLLECTOR_LAST_SCRAPE_TIMESTAMP = Gauge(
    "oci_collector_last_scrape_timestamp",
    "UNIX timestamp of the most recent successful OCI metrics collection.",
)
OCI_COLLECTOR_STATUS = Gauge(
    "oci_collector_status",
    "Status of OCI collector (1 = healthy, 0 = degraded/error).",
)

# Set static default limits
OCI_STORAGE_BLOCK_LIMIT_GB.set(200)
OCI_COMPUTE_AMPERE_OCPUS_LIMIT.set(4.0)
OCI_COMPUTE_AMPERE_MEMORY_GB_LIMIT.set(24.0)
OCI_COMPUTE_AMD_MICRO_LIMIT.set(2)


def update_oci_prometheus_metrics(summary: Union[Dict[str, Any], Any]) -> None:
    """
    Safely updates all Prometheus gauges using the provided summary data (dict or Pydantic model).
    """
    try:
        # Convert Pydantic model to dict if needed
        data = summary.model_dump() if hasattr(summary, "model_dump") else (
            summary.dict() if hasattr(summary, "dict") else summary
        )

        if not isinstance(data, dict):
            return

        # Storage
        storage = data.get("storage", {})
        block_storage = storage.get("block_storage", {})
        if block_storage:
            OCI_STORAGE_BLOCK_ALLOCATED_GB.set(block_storage.get("total_allocated_gb", 0))
            OCI_STORAGE_BLOCK_LIMIT_GB.set(block_storage.get("limit_gb", 200))
            OCI_STORAGE_ORPHAN_VOLUMES_COUNT.set(block_storage.get("orphan_volumes_count", 0))
            OCI_STORAGE_ORPHAN_WASTED_GB.set(block_storage.get("orphan_wasted_gb", 0))

        object_storage = storage.get("object_storage", {})
        if object_storage:
            OCI_STORAGE_OBJECT_STANDARD_GB.set(object_storage.get("standard_gb", 0.0))
            OCI_STORAGE_OBJECT_ARCHIVE_GB.set(object_storage.get("archive_gb", 0.0))

        # Compute
        compute = data.get("compute", {})
        ampere = compute.get("ampere_a1", {})
        if ampere:
            OCI_COMPUTE_AMPERE_OCPUS_ALLOCATED.set(ampere.get("ocpus_allocated", 0.0))
            OCI_COMPUTE_AMPERE_OCPUS_LIMIT.set(ampere.get("limit_ocpus", 4.0))
            OCI_COMPUTE_AMPERE_MEMORY_GB_ALLOCATED.set(ampere.get("memory_gb_allocated", 0.0))
            OCI_COMPUTE_AMPERE_MEMORY_GB_LIMIT.set(ampere.get("limit_memory_gb", 24.0))
            OCI_COMPUTE_AMPERE_INSTANCES_COUNT.set(ampere.get("instances_count", 0))

        amd_micro = compute.get("amd_micro", {})
        if amd_micro:
            OCI_COMPUTE_AMD_MICRO_INSTANCES.set(amd_micro.get("active_instances", 0))
            OCI_COMPUTE_AMD_MICRO_LIMIT.set(amd_micro.get("limit_instances", 2))

        # Networking
        networking = data.get("networking", {})
        if networking:
            vcn_info = networking.get("vcn", {})
            if vcn_info:
                OCI_NETWORK_VCNS_COUNT.set(vcn_info.get("active_vcns", 0))

            pub_ip = networking.get("public_ip", {})
            if pub_ip:
                OCI_NETWORK_RESERVED_IPS_COUNT.set(pub_ip.get("reserved_count", 0))
                OCI_NETWORK_UNASSIGNED_IPS_COUNT.set(pub_ip.get("unassigned_reserved_count", 0))
                OCI_NETWORK_EPHEMERAL_IPS_COUNT.set(pub_ip.get("ephemeral_count", 0))

        # Database
        db_info = data.get("database", {})
        if db_info:
            adb = db_info.get("autonomous_database", {})
            if adb:
                OCI_DATABASE_AUTONOMOUS_COUNT.set(adb.get("active_count", 0))
                OCI_DATABASE_STORAGE_GB.set(adb.get("allocated_storage_gb", 0.0))

        # API Usage
        api_usage = data.get("api_usage", {})
        if api_usage:
            OCI_API_CALLS_TODAY.set(api_usage.get("calls_today", 0))
            OCI_API_DAILY_LIMIT.set(api_usage.get("daily_limit", 10000))

        # Collector Status
        overall_status = data.get("status", "healthy")
        OCI_COLLECTOR_STATUS.set(1 if overall_status == "healthy" else 0)
        OCI_COLLECTOR_LAST_SCRAPE_TIMESTAMP.set(time.time())

    except Exception as e:
        logger.warning(f"Error updating Prometheus gauges: {e}")


def get_latest_metrics() -> bytes:
    """
    Renders all registered Prometheus metrics into text format bytes.
    """
    return generate_latest(REGISTRY)
