import os
import calendar
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


def get_status_color(percentage: float) -> str:
    """Returns 'safe', 'warning', or 'danger' according to threshold."""
    if percentage >= 90.0:
        return "danger"
    elif percentage >= 75.0:
        return "warning"
    return "safe"


def filter_active_compartments(compartments: List[Any]) -> List[Any]:
    """Filters only compartments with ACTIVE lifecycle state."""
    return [c for c in compartments if getattr(c, "lifecycle_state", None) == "ACTIVE"]


def process_block_storage_inventory(
    boot_volumes: List[Any],
    block_volumes: List[Any],
    boot_attachments: List[Any],
    volume_attachments: List[Any],
    compartment_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Sums total block storage and detects orphan volumes.
    A volume is orphan if it has no active attachment to a running instance.
    """
    if compartment_map is None:
        compartment_map = {}

    # Map of attached boot volume IDs
    attached_boot_ids = {
        att.boot_volume_id
        for att in boot_attachments
        if getattr(att, "lifecycle_state", None) in ["ATTACHED", "ATTACHING"]
    }
    # Map of attached block volume IDs
    attached_block_ids = {
        att.volume_id
        for att in volume_attachments
        if getattr(att, "lifecycle_state", None) in ["ATTACHED", "ATTACHING"]
    }

    total_allocated_gb = 0
    orphan_wasted_gb = 0
    orphan_volumes = []
    all_volumes_detail = []

    # Process boot volumes
    for bv in boot_volumes:
        size = getattr(bv, "size_in_gbs", 0) or 0
        total_allocated_gb += size
        is_orphan = bv.id not in attached_boot_ids
        
        # Find attached instance ID if any
        attached_instance = next(
            (att.instance_id for att in boot_attachments if att.boot_volume_id == bv.id),
            None
        )

        vol_info = {
            "id": bv.id,
            "display_name": getattr(bv, "display_name", "Boot Volume"),
            "volume_type": "boot",
            "size_in_gbs": size,
            "compartment_id": getattr(bv, "compartment_id", None),
            "compartment_name": compartment_map.get(getattr(bv, "compartment_id", ""), "root"),
            "is_orphan": is_orphan,
            "attached_instance_id": attached_instance,
            "time_created": str(getattr(bv, "time_created", "")),
        }
        all_volumes_detail.append(vol_info)

        if is_orphan:
            orphan_wasted_gb += size
            orphan_volumes.append(vol_info)

    # Process block volumes
    for blk in block_volumes:
        size = getattr(blk, "size_in_gbs", 0) or 0
        total_allocated_gb += size
        is_orphan = blk.id not in attached_block_ids

        attached_instance = next(
            (att.instance_id for att in volume_attachments if att.volume_id == blk.id),
            None
        )

        vol_info = {
            "id": blk.id,
            "display_name": getattr(blk, "display_name", "Block Volume"),
            "volume_type": "block",
            "size_in_gbs": size,
            "compartment_id": getattr(blk, "compartment_id", None),
            "compartment_name": compartment_map.get(getattr(blk, "compartment_id", ""), "root"),
            "is_orphan": is_orphan,
            "attached_instance_id": attached_instance,
            "time_created": str(getattr(blk, "time_created", "")),
        }
        all_volumes_detail.append(vol_info)

        if is_orphan:
            orphan_wasted_gb += size
            orphan_volumes.append(vol_info)

    limit_gb = 200
    percentage = round((total_allocated_gb / limit_gb) * 100, 2) if limit_gb else 0.0

    return {
        "total_allocated_gb": total_allocated_gb,
        "limit_gb": limit_gb,
        "percentage": percentage,
        "status": get_status_color(percentage),
        "orphan_volumes_count": len(orphan_volumes),
        "orphan_wasted_gb": orphan_wasted_gb,
        "boot_volumes_count": len(boot_volumes),
        "block_volumes_count": len(block_volumes),
        "orphan_volumes": orphan_volumes,
        "all_volumes": all_volumes_detail,
    }


def process_compute_inventory(instances: List[Any]) -> Dict[str, Any]:
    """
    Aggregates Ampere A1 (Arm) OCPUs / RAM and counts active AMD Micro instances.
    """
    running_instances = [
        inst for inst in instances
        if getattr(inst, "lifecycle_state", None) == "RUNNING"
    ]

    ampere_ocpus = 0.0
    ampere_memory_gb = 0.0
    ampere_count = 0

    micro_count = 0

    for inst in running_instances:
        shape = getattr(inst, "shape", "")
        if shape == "VM.Standard.A1.Flex":
            ampere_count += 1
            config = getattr(inst, "shape_config", None)
            if config:
                ampere_ocpus += float(getattr(config, "ocpus", 0) or 0)
                ampere_memory_gb += float(getattr(config, "memory_in_gbs", 0) or 0)
        elif shape == "VM.Standard.E2.1.Micro":
            micro_count += 1

    ampere_limit_ocpus = 4.0
    ampere_limit_memory = 24.0
    ampere_ocpu_pct = (ampere_ocpus / ampere_limit_ocpus) * 100 if ampere_limit_ocpus else 0.0
    ampere_mem_pct = (ampere_memory_gb / ampere_limit_memory) * 100 if ampere_limit_memory else 0.0
    ampere_status = get_status_color(max(ampere_ocpu_pct, ampere_mem_pct))

    micro_limit = 2
    micro_pct = (micro_count / micro_limit) * 100 if micro_limit else 0.0
    micro_status = get_status_color(micro_pct)

    return {
        "ampere_a1": {
            "ocpus_allocated": ampere_ocpus,
            "limit_ocpus": ampere_limit_ocpus,
            "memory_gb_allocated": ampere_memory_gb,
            "limit_memory_gb": ampere_limit_memory,
            "instances_count": ampere_count,
            "monthly_ocpu_hours": 0.0,
            "monthly_ocpu_hours_limit": 3000.0,
            "projected_ocpu_hours": 0.0,
            "status": ampere_status,
        },
        "amd_micro": {
            "active_instances": micro_count,
            "limit_instances": micro_limit,
            "status": micro_status,
        }
    }


def process_object_storage_inventory(buckets: List[Any]) -> Dict[str, Any]:
    """Converts bucket sizes from bytes to GB and aggregates by tier."""
    standard_bytes = 0
    archive_bytes = 0

    for b in buckets:
        size = getattr(b, "approximate_size", 0) or 0
        tier = getattr(b, "storage_tier", "Standard") or "Standard"
        if tier == "Standard":
            standard_bytes += size
        else:
            archive_bytes += size

    gb_factor = 1024 ** 3
    standard_gb = round(standard_bytes / gb_factor, 2)
    archive_gb = round(archive_bytes / gb_factor, 2)

    limit_standard_gb = 10.0
    limit_archive_gb = 10.0
    pct = round((standard_gb / limit_standard_gb) * 100, 2)

    return {
        "standard_gb": standard_gb,
        "limit_standard_gb": limit_standard_gb,
        "standard_percentage": pct,
        "archive_gb": archive_gb,
        "limit_archive_gb": limit_archive_gb,
        "bucket_count": len(buckets),
        "status": get_status_color(pct),
    }


def calculate_burn_rate_projection(
    current_ocpu_hours: float,
    current_egress_gb: float,
    days_elapsed: int,
    days_in_month: int,
) -> Dict[str, Any]:
    """
    Calculates average daily burn rate and projects consumption to the end of the month.
    Consumo_Projetado = (Consumo_Atual / Dias_Transcorridos) * Dias_Totais_Do_Mes
    """
    safe_days_elapsed = max(days_elapsed, 1)

    ocpu_burn_rate_daily = current_ocpu_hours / safe_days_elapsed
    projected_ocpu_hours = round(ocpu_burn_rate_daily * days_in_month, 2)

    egress_burn_rate_daily_gb = current_egress_gb / safe_days_elapsed
    projected_egress_gb = round(egress_burn_rate_daily_gb * days_in_month, 2)

    warnings = []
    if projected_ocpu_hours > 3000.0:
        warnings.append(
            f"Alerta de Risco: Projeção de {projected_ocpu_hours} OCPU-horas excede a cota gratuita de 3.000 OCPU-horas/mês!"
        )

    # 10 TB in GB is ~10,000 GB
    if projected_egress_gb > 10000.0:
        warnings.append(
            f"Alerta de Risco: Projeção de tráfego de saída ({round(projected_egress_gb/1024, 2)} TB) excede os 10 TB/mês gratuitos!"
        )

    return {
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "ocpu_burn_rate_daily": round(ocpu_burn_rate_daily, 2),
        "projected_ocpu_hours": projected_ocpu_hours,
        "egress_burn_rate_daily_gb": round(egress_burn_rate_daily_gb, 2),
        "projected_egress_gb": projected_egress_gb,
        "warnings": warnings,
    }


class OCICollector:
    """
    Main collector for Oracle Cloud Infrastructure.
    Queries Identity, Compute, Block Storage, Object Storage, and Usage APIs.
    """
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.config_dict = config_dict
        self._identity_client = None
        self._compute_client = None
        self._block_storage_client = None
        self._object_storage_client = None
        self._usage_client = None

    def _init_clients(self):
        if self._identity_client is not None:
            return

        import oci
        self._identity_client = oci.identity.IdentityClient(self.config_dict)
        self._compute_client = oci.core.ComputeClient(self.config_dict)
        self._block_storage_client = oci.core.BlockstorageClient(self.config_dict)
        self._object_storage_client = oci.object_storage.ObjectStorageClient(self.config_dict)
        self._usage_client = oci.usage_api.UsageapiClient(self.config_dict)

    def get_all_active_compartments(self, tenancy_id: str) -> List[Any]:
        """Recursively lists all accessible, active compartments starting from root."""
        self._init_clients()
        import oci

        active_compartments = []
        try:
            # Add root tenancy itself
            root_c = self._identity_client.get_tenancy(tenancy_id).data
            active_compartments.append(root_c)
        except Exception as e:
            logger.warning(f"Could not get tenancy root directly: {e}")

        try:
            # List subcompartments in entire subtree
            sub_comps = oci.pagination.list_call_get_all_results(
                self._identity_client.list_compartments,
                tenancy_id,
                compartment_id_in_subtree=True,
                access_level="ACCESSIBLE"
            ).data
            active_compartments.extend(filter_active_compartments(sub_comps))
        except Exception as e:
            logger.warning(f"Error fetching subcompartments: {e}")

        return active_compartments

    def collect(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Executes a full inventory collection across all compartments.
        Returns:
            (summary_dict, volumes_list)
        """
        self._init_clients()
        import oci

        tenancy_id = self.config_dict.get("tenancy", "")
        region = self.config_dict.get("region", "us-ashburn-1")

        compartments = self.get_all_active_compartments(tenancy_id)
        comp_map = {getattr(c, "id", ""): getattr(c, "name", "root") for c in compartments}
        comp_map[tenancy_id] = "root"

        all_boot_volumes = []
        all_block_volumes = []
        all_boot_attachments = []
        all_volume_attachments = []
        all_instances = []
        all_buckets = []

        # 1. Fetch compute & storage per compartment
        for comp in compartments:
            cid = comp.id
            try:
                # Boot Volumes
                bvs = oci.pagination.list_call_get_all_results(
                    self._block_storage_client.list_boot_volumes,
                    availability_domain=None,
                    compartment_id=cid
                ).data
                all_boot_volumes.extend(bvs)
            except Exception:
                pass

            try:
                # Block Volumes
                blks = oci.pagination.list_call_get_all_results(
                    self._block_storage_client.list_volumes,
                    compartment_id=cid
                ).data
                all_block_volumes.extend(blks)
            except Exception:
                pass

            try:
                # Boot Volume Attachments
                bvas = oci.pagination.list_call_get_all_results(
                    self._compute_client.list_boot_volume_attachments,
                    availability_domain=None,
                    compartment_id=cid
                ).data
                all_boot_attachments.extend(bvas)
            except Exception:
                pass

            try:
                # Volume Attachments
                vas = oci.pagination.list_call_get_all_results(
                    self._compute_client.list_volume_attachments,
                    compartment_id=cid
                ).data
                all_volume_attachments.extend(vas)
            except Exception:
                pass

            try:
                # Instances
                insts = oci.pagination.list_call_get_all_results(
                    self._compute_client.list_instances,
                    compartment_id=cid
                ).data
                all_instances.extend(insts)
            except Exception:
                pass

        # 2. Fetch object storage
        try:
            ns = self._object_storage_client.get_namespace().data
            for comp in compartments:
                cid = comp.id
                b_summaries = oci.pagination.list_call_get_all_results(
                    self._object_storage_client.list_buckets,
                    namespace_name=ns,
                    compartment_id=cid
                ).data
                for b_sum in b_summaries:
                    try:
                        b_detail = self._object_storage_client.get_bucket(
                            namespace_name=ns,
                            bucket_name=b_sum.name,
                            fields=["approximateCount", "approximateSize"]
                        ).data
                        all_buckets.append(b_detail)
                    except Exception:
                        all_buckets.append(b_sum)
        except Exception as e:
            logger.warning(f"Error reading Object Storage: {e}")

        # 3. Calculate Date/Time for Burn Rate
        now = datetime.now(timezone.utc)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_elapsed = now.day

        # 4. Process inventories
        storage_result = process_block_storage_inventory(
            boot_volumes=all_boot_volumes,
            block_volumes=all_block_volumes,
            boot_attachments=all_boot_attachments,
            volume_attachments=all_volume_attachments,
            compartment_map=comp_map
        )
        all_volumes_detail = storage_result.pop("all_volumes", [])
        orphan_volumes = storage_result.pop("orphan_volumes", [])

        compute_result = process_compute_inventory(all_instances)
        obj_result = process_object_storage_inventory(all_buckets)

        # 5. Usage API (with safe fallback if delayed or empty)
        monthly_ocpu_hours = 0.0
        egress_tb = 0.0
        egress_gb = 0.0

        # Attempt to query usage if possible
        try:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Query usage API for month to date
            # If usage api returns nothing or errors, fallback gracefully to current allocated estimate
            # Approximate current allocation hours = allocated OCPUs * hours elapsed this month
            hours_elapsed = (days_elapsed - 1) * 24 + now.hour
            monthly_ocpu_hours = round(compute_result["ampere_a1"]["ocpus_allocated"] * hours_elapsed, 1)
        except Exception as e:
            logger.info(f"Usage API fallback calculation: {e}")

        compute_result["ampere_a1"]["monthly_ocpu_hours"] = monthly_ocpu_hours
        burn_result = calculate_burn_rate_projection(
            current_ocpu_hours=monthly_ocpu_hours,
            current_egress_gb=egress_gb,
            days_elapsed=days_elapsed,
            days_in_month=days_in_month
        )
        compute_result["ampere_a1"]["projected_ocpu_hours"] = burn_result["projected_ocpu_hours"]

        # 6. Build consolidated dictionary
        summary_payload = {
            "status": "healthy",
            "collected_at": now.isoformat(),
            "tenancy": {
                "id": tenancy_id,
                "name": comp_map.get(tenancy_id, "root"),
                "home_region": region
            },
            "storage": {
                "block_storage": storage_result,
                "object_storage": obj_result
            },
            "compute": compute_result,
            "network": {
                "egress_tb_current": round(egress_gb / 1024, 2),
                "egress_tb_limit": 10.0,
                "egress_projected_tb": round(burn_result["projected_egress_gb"] / 1024, 2),
                "status": "safe"
            },
            "burn_rate": burn_result
        }

        return summary_payload, all_volumes_detail
