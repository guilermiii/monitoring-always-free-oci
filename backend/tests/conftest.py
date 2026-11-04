import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class MockRedis:
    """Async in-memory mock for Redis."""
    def __init__(self):
        self._store = {}
        self._ttls = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        self._store[key] = str(value)
        if ex:
            self._ttls[key] = ex
        return True

    async def incrby(self, key: str, amount: int = 1):
        current = int(self._store.get(key, 0) or 0)
        current += amount
        self._store[key] = str(current)
        return current

    async def expire(self, key: str, time: int):
        self._ttls[key] = time
        return True

    async def delete(self, key: str):
        if key in self._store:
            del self._store[key]
        return True

    async def ping(self):
        return True

    async def aclose(self):
        pass


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
def sample_compartments():
    c_root = MagicMock()
    c_root.id = "ocid1.tenancy.oc1..root"
    c_root.name = "root"
    c_root.lifecycle_state = "ACTIVE"

    c_sub1 = MagicMock()
    c_sub1.id = "ocid1.compartment.oc1..dev"
    c_sub1.name = "dev-workloads"
    c_sub1.lifecycle_state = "ACTIVE"

    c_deleted = MagicMock()
    c_deleted.id = "ocid1.compartment.oc1..deleted"
    c_deleted.name = "old-workloads"
    c_deleted.lifecycle_state = "DELETED"

    return [c_root, c_sub1, c_deleted]


@pytest.fixture
def sample_volumes_and_attachments():
    """
    Scenario:
    - BootVol1 (50 GB): ATTACHED to Instance 1 -> Not orphan
    - BootVol2 (50 GB): NO attachment (instance terminated) -> ORPHAN!
    - BlockVol1 (50 GB): ATTACHED to Instance 1 -> Not orphan
    - BlockVol2 (50 GB): NO attachment -> ORPHAN!
    Total storage: 200 GB.
    Orphan storage: 100 GB.
    """
    # Boot Volumes
    bv1 = MagicMock()
    bv1.id = "ocid1.bootvolume.oc1..bv1"
    bv1.display_name = "boot-vm-prod"
    bv1.size_in_gbs = 50
    bv1.lifecycle_state = "AVAILABLE"
    bv1.compartment_id = "ocid1.tenancy.oc1..root"
    bv1.time_created = "2026-01-01T00:00:00Z"

    bv2 = MagicMock()
    bv2.id = "ocid1.bootvolume.oc1..bv2_orphan"
    bv2.display_name = "boot-old-dev-deleted-vm"
    bv2.size_in_gbs = 50
    bv2.lifecycle_state = "AVAILABLE"
    bv2.compartment_id = "ocid1.compartment.oc1..dev"
    bv2.time_created = "2026-02-01T00:00:00Z"

    # Block Volumes
    blk1 = MagicMock()
    blk1.id = "ocid1.volume.oc1..blk1"
    blk1.display_name = "data-disk-prod"
    blk1.size_in_gbs = 50
    blk1.lifecycle_state = "AVAILABLE"
    blk1.compartment_id = "ocid1.tenancy.oc1..root"
    blk1.time_created = "2026-01-05T00:00:00Z"

    blk2 = MagicMock()
    blk2.id = "ocid1.volume.oc1..blk2_orphan"
    blk2.display_name = "scratch-unattached"
    blk2.size_in_gbs = 50
    blk2.lifecycle_state = "AVAILABLE"
    blk2.compartment_id = "ocid1.compartment.oc1..dev"
    blk2.time_created = "2026-02-15T00:00:00Z"

    # Attachments
    bva1 = MagicMock()
    bva1.boot_volume_id = "ocid1.bootvolume.oc1..bv1"
    bva1.instance_id = "ocid1.instance.oc1..inst1"
    bva1.lifecycle_state = "ATTACHED"

    va1 = MagicMock()
    va1.volume_id = "ocid1.volume.oc1..blk1"
    va1.instance_id = "ocid1.instance.oc1..inst1"
    va1.lifecycle_state = "ATTACHED"

    return {
        "boot_volumes": [bv1, bv2],
        "block_volumes": [blk1, blk2],
        "boot_attachments": [bva1],
        "volume_attachments": [va1],
    }


@pytest.fixture
def sample_compute_instances():
    # Ampere A1 (Arm) flex instance 1: 2 OCPU, 12 GB RAM
    inst1 = MagicMock()
    inst1.id = "ocid1.instance.oc1..inst1"
    inst1.display_name = "arm-app-server"
    inst1.shape = "VM.Standard.A1.Flex"
    inst1.shape_config = MagicMock(ocpus=2.0, memory_in_gbs=12.0)
    inst1.lifecycle_state = "RUNNING"
    inst1.compartment_id = "ocid1.tenancy.oc1..root"

    # Ampere A1 (Arm) flex instance 2: 2 OCPU, 12 GB RAM
    inst2 = MagicMock()
    inst2.id = "ocid1.instance.oc1..inst2"
    inst2.display_name = "arm-db-server"
    inst2.shape = "VM.Standard.A1.Flex"
    inst2.shape_config = MagicMock(ocpus=2.0, memory_in_gbs=12.0)
    inst2.lifecycle_state = "RUNNING"
    inst2.compartment_id = "ocid1.compartment.oc1..dev"

    # AMD Micro instance: 1 instance RUNNING
    inst3 = MagicMock()
    inst3.id = "ocid1.instance.oc1..inst3"
    inst3.display_name = "micro-vpn"
    inst3.shape = "VM.Standard.E2.1.Micro"
    inst3.shape_config = MagicMock(ocpus=1.0, memory_in_gbs=1.0)
    inst3.lifecycle_state = "RUNNING"
    inst3.compartment_id = "ocid1.tenancy.oc1..root"

    # Terminated instance (should be ignored)
    inst_term = MagicMock()
    inst_term.id = "ocid1.instance.oc1..inst_term"
    inst_term.display_name = "terminated-vm"
    inst_term.shape = "VM.Standard.E2.1.Micro"
    inst_term.lifecycle_state = "TERMINATED"
    inst_term.compartment_id = "ocid1.tenancy.oc1..root"

    return [inst1, inst2, inst3, inst_term]


@pytest.fixture
def sample_object_storage():
    b1 = MagicMock()
    b1.name = "backup-bucket"
    b1.storage_tier = "Standard"
    b1.approximate_size = 3 * 1024 * 1024 * 1024  # 3 GB
    b1.approximate_count = 120

    b2 = MagicMock()
    b2.name = "archive-bucket"
    b2.storage_tier = "Archive"
    b2.approximate_size = 1 * 1024 * 1024 * 1024  # 1 GB
    b2.approximate_count = 10

    return {
        "namespace": "mytenancy-ns",
        "buckets": [b1, b2]
    }


@pytest.fixture
def sample_vcns():
    v1 = MagicMock()
    v1.id = "ocid1.vcn.oc1..vcn1"
    v1.display_name = "prod-vcn"
    v1.cidr_block = "10.0.0.0/16"
    v1.lifecycle_state = "AVAILABLE"
    v1.compartment_id = "ocid1.tenancy.oc1..root"

    v_term = MagicMock()
    v_term.id = "ocid1.vcn.oc1..vcn_term"
    v_term.display_name = "old-vcn"
    v_term.cidr_block = "172.16.0.0/16"
    v_term.lifecycle_state = "TERMINATED"
    v_term.compartment_id = "ocid1.tenancy.oc1..root"

    return [v1, v_term]


@pytest.fixture
def sample_public_ips():
    # 1 Reserved IP attached
    ip1 = MagicMock()
    ip1.id = "ocid1.publicip.oc1..ip1"
    ip1.ip_address = "129.148.1.10"
    ip1.display_name = "vault-ip"
    ip1.lifetime = "RESERVED"
    ip1.assigned_entity_id = "ocid1.vnic.oc1..vnic1"
    ip1.assigned_entity_type = "VNIC"
    ip1.lifecycle_state = "AVAILABLE"
    ip1.compartment_id = "ocid1.tenancy.oc1..root"

    # 1 Reserved IP unassigned (ORPHAN IP!)
    ip2 = MagicMock()
    ip2.id = "ocid1.publicip.oc1..ip2_unassigned"
    ip2.ip_address = "129.148.1.20"
    ip2.display_name = "unassigned-static-ip"
    ip2.lifetime = "RESERVED"
    ip2.assigned_entity_id = None
    ip2.assigned_entity_type = None
    ip2.lifecycle_state = "AVAILABLE"
    ip2.compartment_id = "ocid1.tenancy.oc1..root"

    # 1 Ephemeral IP
    ip3 = MagicMock()
    ip3.id = "ocid1.publicip.oc1..ip3_ephemeral"
    ip3.ip_address = "129.148.1.30"
    ip3.display_name = "ephemeral-compute-ip"
    ip3.lifetime = "EPHEMERAL"
    ip3.assigned_entity_id = "ocid1.vnic.oc1..vnic2"
    ip3.assigned_entity_type = "VNIC"
    ip3.lifecycle_state = "AVAILABLE"
    ip3.compartment_id = "ocid1.tenancy.oc1..root"

    # Terminated IP
    ip_term = MagicMock()
    ip_term.id = "ocid1.publicip.oc1..ip_term"
    ip_term.ip_address = "129.148.1.40"
    ip_term.display_name = "terminated-ip"
    ip_term.lifetime = "RESERVED"
    ip_term.lifecycle_state = "TERMINATED"

    return [ip1, ip2, ip3, ip_term]


@pytest.fixture
def sample_load_balancers():
    # Flexible Load Balancer
    lb1 = MagicMock()
    lb1.id = "ocid1.loadbalancer.oc1..lb1"
    lb1.display_name = "web-alb"
    lb1.shape_name = "10Mbps-Micro"
    lb1.lifecycle_state = "ACTIVE"
    lb1.ip_addresses = [MagicMock(ip_address="129.148.2.1", is_public=True)]
    lb1.compartment_id = "ocid1.tenancy.oc1..root"

    lb_deleted = MagicMock()
    lb_deleted.id = "ocid1.loadbalancer.oc1..lb_del"
    lb_deleted.display_name = "deleted-alb"
    lb_deleted.shape_name = "10Mbps-Micro"
    lb_deleted.lifecycle_state = "DELETED"

    # Network Load Balancer (NLB)
    nlb1 = MagicMock()
    nlb1.id = "ocid1.networkloadbalancer.oc1..nlb1"
    nlb1.display_name = "internal-nlb"
    nlb1.lifecycle_state = "ACTIVE"
    nlb1.ip_addresses = [MagicMock(ip_address="10.0.1.5", is_public=False)]
    nlb1.compartment_id = "ocid1.tenancy.oc1..root"

    return {
        "load_balancers": [lb1, lb_deleted],
        "network_load_balancers": [nlb1],
    }


@pytest.fixture
def sample_autonomous_databases():
    db1 = MagicMock()
    db1.id = "ocid1.autonomousdatabase.oc1..db1"
    db1.display_name = "app-db"
    db1.db_name = "appdb"
    db1.is_free_tier = True
    db1.cpu_core_count = 1
    db1.data_storage_size_in_gbs = 20
    db1.db_workload = "OLTP"
    db1.lifecycle_state = "AVAILABLE"
    db1.compartment_id = "ocid1.tenancy.oc1..root"

    db_deleted = MagicMock()
    db_deleted.id = "ocid1.autonomousdatabase.oc1..db_del"
    db_deleted.display_name = "old-db"
    db_deleted.is_free_tier = True
    db_deleted.lifecycle_state = "TERMINATED"

    return [db1, db_deleted]


@pytest.fixture
def sample_bastions():
    b1 = MagicMock()
    b1.id = "ocid1.bastion.oc1..b1"
    b1.name = "mgmt-bastion"
    b1.lifecycle_state = "ACTIVE"
    b1.compartment_id = "ocid1.tenancy.oc1..root"

    b_del = MagicMock()
    b_del.id = "ocid1.bastion.oc1..b_del"
    b_del.name = "old-bastion"
    b_del.lifecycle_state = "DELETED"

    return [b1, b_del]
