from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: str = Field(default="alive", description="Liveness probe status ('alive')")
    timestamp: str = Field(description="ISO 8601 timestamp of the probe check")


class ReadinessResponse(BaseModel):
    status: str = Field(default="ready", description="Readiness status ('ready' or 'not_ready')")
    redis_connected: bool = Field(description="Indicates whether Redis is reachable and responding to ping")
    oci_configured: bool = Field(description="Indicates whether OCI credentials and config are present")
    timestamp: str = Field(description="ISO 8601 timestamp of the probe check")
    details: Optional[str] = Field(default=None, description="Diagnostic information if not ready")


class StartupResponse(BaseModel):
    status: str = Field(default="started", description="Startup probe status ('started' or 'starting')")
    app_started: bool = Field(description="True if application lifespan startup has completed")
    timestamp: str = Field(description="ISO 8601 timestamp of the probe check")


class GeneralHealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall health status ('healthy' or 'degraded')")
    redis_connected: bool = Field(description="Redis connection status")
    oci_configured: bool = Field(description="OCI configuration status")
    timestamp: str = Field(description="ISO 8601 timestamp of the health check")
    message: Optional[str] = Field(default=None, description="Diagnostic message")


class RootResponse(BaseModel):
    app: str = Field(default="OCI Always Free Monitor API", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    docs_url: str = Field(default="/docs", description="Swagger UI documentation URL")
    api_v1: str = Field(default="/api/v1/summary", description="V1 summary API URL")
    metrics_url: str = Field(default="/metrics", description="Prometheus metrics scrape URL")


class HealthResponse(BaseModel):
    status: str = "ok"
    redis_connected: bool = True
    oci_configured: bool = True
    message: Optional[str] = None


class TenancyInfo(BaseModel):
    id: str
    name: str
    home_region: str


class BlockStorageSummary(BaseModel):
    total_allocated_gb: int
    limit_gb: int = 200
    percentage: float
    status: str  # "safe" | "warning" | "danger"
    orphan_volumes_count: int
    orphan_wasted_gb: int
    boot_volumes_count: int
    block_volumes_count: int


class ObjectStorageSummary(BaseModel):
    standard_gb: float
    limit_standard_gb: float = 10.0
    standard_percentage: float
    archive_gb: float
    limit_archive_gb: float = 10.0
    bucket_count: int
    status: str = "safe"


class StorageSummary(BaseModel):
    block_storage: BlockStorageSummary
    object_storage: ObjectStorageSummary


class AmpereA1Summary(BaseModel):
    ocpus_allocated: float
    limit_ocpus: float = 4.0
    memory_gb_allocated: float
    limit_memory_gb: float = 24.0
    instances_count: int
    monthly_ocpu_hours: float = 0.0
    monthly_ocpu_hours_limit: float = 3000.0
    projected_ocpu_hours: float = 0.0
    status: str = "safe"


class AmdMicroSummary(BaseModel):
    active_instances: int
    limit_instances: int = 2
    status: str = "safe"


class ComputeSummary(BaseModel):
    ampere_a1: AmpereA1Summary
    amd_micro: AmdMicroSummary


class NetworkSummary(BaseModel):
    egress_tb_current: float = 0.0
    egress_tb_limit: float = 10.0
    egress_projected_tb: float = 0.0
    status: str = "safe"


class VcnSummary(BaseModel):
    active_vcns: int
    limit_vcns: int = 2
    percentage: float
    status: str = "safe"


class PublicIpSummary(BaseModel):
    reserved_count: int
    reserved_limit: int = 1
    unassigned_reserved_count: int
    ephemeral_count: int
    total_active_ips: int = 0
    percentage: float
    status: str = "safe"


class LoadBalancerSummary(BaseModel):
    flexible_lb_count: int
    limit_flexible_lb: int = 1
    nlb_count: int
    limit_nlb: int = 1
    status: str = "safe"


class BastionSummary(BaseModel):
    active_bastions: int
    limit_bastions: int = 2
    status: str = "safe"


class NetworkingFullSummary(BaseModel):
    vcn: VcnSummary
    public_ip: PublicIpSummary
    load_balancer: LoadBalancerSummary
    bastion: BastionSummary
    egress: NetworkSummary


class AutonomousDatabaseSummary(BaseModel):
    active_count: int
    limit_count: int = 2
    allocated_storage_gb: float
    limit_storage_gb: float = 40.0
    percentage: float
    status: str = "safe"


class DatabaseSummary(BaseModel):
    autonomous_database: AutonomousDatabaseSummary


class BurnRateSummary(BaseModel):
    days_elapsed: int
    days_in_month: int
    ocpu_burn_rate_daily: float = 0.0
    egress_burn_rate_daily_gb: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class ApiUsageSummary(BaseModel):
    calls_today: int
    daily_limit: int = 10000
    calls_last_run: int = 0
    rate_limit_per_minute: int = 3000
    percentage: float = 0.0
    status: str = "safe"  # "safe" | "warning" | "danger"


class SummaryResponse(BaseModel):
    status: str = "healthy"
    collected_at: str
    tenancy: TenancyInfo
    storage: StorageSummary
    compute: ComputeSummary
    network: NetworkSummary
    networking: Optional[NetworkingFullSummary] = None
    database: Optional[DatabaseSummary] = None
    burn_rate: BurnRateSummary
    api_usage: Optional[ApiUsageSummary] = None


class VolumeDetail(BaseModel):
    id: str
    display_name: str
    volume_type: str  # "boot" | "block"
    size_in_gbs: int
    compartment_id: Optional[str] = None
    compartment_name: Optional[str] = None
    is_orphan: bool
    attached_instance_id: Optional[str] = None
    lifecycle_state: Optional[str] = "AVAILABLE"
    time_created: Optional[str] = None


class VcnDetail(BaseModel):
    id: str
    display_name: str
    cidr_block: Optional[str] = None
    compartment_id: Optional[str] = None
    compartment_name: Optional[str] = None
    lifecycle_state: str = "AVAILABLE"
    time_created: Optional[str] = None


class PublicIpDetail(BaseModel):
    id: str
    ip_address: str
    display_name: str = "public-ip"
    lifetime: str = "RESERVED"  # "RESERVED" | "EPHEMERAL"
    is_unassigned: bool = False
    assigned_entity_id: Optional[str] = None
    assigned_entity_type: Optional[str] = None
    compartment_id: Optional[str] = None
    compartment_name: Optional[str] = None
    lifecycle_state: str = "AVAILABLE"


class LoadBalancerDetail(BaseModel):
    id: str
    display_name: str
    lb_type: str = "flexible"  # "flexible" | "network"
    shape_name: str = "flexible"
    ip_addresses: List[str] = Field(default_factory=list)
    compartment_id: Optional[str] = None
    compartment_name: Optional[str] = None
    lifecycle_state: str = "ACTIVE"


class DatabaseDetail(BaseModel):
    id: str
    display_name: str
    db_name: str
    is_free_tier: bool
    cpu_core_count: int
    data_storage_size_in_gbs: int
    db_workload: str
    compartment_id: Optional[str] = None
    compartment_name: Optional[str] = None
    lifecycle_state: str = "AVAILABLE"


class NetworkInventoryResponse(BaseModel):
    vcns: List[VcnDetail] = Field(default_factory=list, description="List of Virtual Cloud Networks")
    public_ips: List[PublicIpDetail] = Field(default_factory=list, description="List of active Public IPs")
    unassigned_ips: List[PublicIpDetail] = Field(default_factory=list, description="List of unassigned (orphan) Public IPs")
    load_balancers: List[LoadBalancerDetail] = Field(default_factory=list, description="List of Load Balancers")

