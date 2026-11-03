import React, { useState, useEffect } from 'react';
import {
  HardDrive,
  Cpu,
  Server,
  Database,
  ArrowUpRight,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import Header from './components/Header';
import MetricCard from './components/MetricCard';
import OrphanAlert from './components/OrphanAlert';
import BurnRateCard from './components/BurnRateCard';
import VolumesTable from './components/VolumesTable';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [volumes, setVolumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [sumRes, volRes] = await Promise.all([
        fetch('/api/v1/summary'),
        fetch('/api/v1/storage/volumes'),
      ]);

      if (!sumRes.ok) {
        throw new Error(`Erro ao consultar resumo: HTTP ${sumRes.status}`);
      }
      const sumData = await sumRes.json();
      setSummary(sumData);

      if (volRes.ok) {
        const volData = await volRes.json();
        setVolumes(volData);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Falha ao conectar à API');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleForceRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch('/api/v1/refresh', { method: 'POST' });
      if (!res.ok) throw new Error('Falha na sincronização imediata');
      await fetchData();
    } catch (err) {
      console.error(err);
      setError(err.message);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const scrollToVolumes = () => {
    const el = document.getElementById('volumes-inventory');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0D1117] flex flex-col items-center justify-center text-slate-400 gap-4">
        <RefreshCw className="w-8 h-8 text-red-500 animate-spin" />
        <p className="text-sm font-medium">Carregando métricas da Oracle Cloud...</p>
      </div>
    );
  }

  const blockStorage = summary?.storage?.block_storage || {};
  const objectStorage = summary?.storage?.object_storage || {};
  const computeAmpere = summary?.compute?.ampere_a1 || {};
  const computeMicro = summary?.compute?.amd_micro || {};
  const network = summary?.network || {};
  const burnRate = summary?.burn_rate || {};

  return (
    <div className="min-h-screen bg-[#0D1117] flex flex-col selection:bg-red-500 selection:text-white">
      <Header
        tenancy={summary?.tenancy}
        collectedAt={summary?.collected_at}
        isRefreshing={refreshing}
        onRefresh={handleForceRefresh}
      />

      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
        {/* Error notification if any */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-400" />
              <span>{error}</span>
            </div>
            <button
              onClick={fetchData}
              className="text-xs px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 font-medium"
            >
              Tentar Novamente
            </button>
          </div>
        )}

        {/* Orphan Disks Warning Card */}
        <OrphanAlert
          count={blockStorage.orphan_volumes_count}
          wastedGb={blockStorage.orphan_wasted_gb}
          onScrollToVolumes={scrollToVolumes}
        />

        {/* Primary Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* 1. Block Storage */}
          <MetricCard
            title="Armazenamento de Blocos"
            subtitle="Boot + Block Volumes"
            icon={HardDrive}
            used={blockStorage.total_allocated_gb || 0}
            limit={blockStorage.limit_gb || 200}
            unit="GB"
            percentage={blockStorage.percentage || 0}
            status={blockStorage.status}
          >
            <div className="flex justify-between">
              <span>Boot Volumes:</span>
              <span className="text-slate-200 font-medium">{blockStorage.boot_volumes_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span>Block Volumes:</span>
              <span className="text-slate-200 font-medium">{blockStorage.block_volumes_count || 0}</span>
            </div>
            {blockStorage.orphan_volumes_count > 0 && (
              <div className="flex justify-between text-amber-400 font-medium">
                <span>Discos Órfãos:</span>
                <span>{blockStorage.orphan_volumes_count} ({blockStorage.orphan_wasted_gb} GB)</span>
              </div>
            )}
          </MetricCard>

          {/* 2. Compute Ampere A1 (Arm) */}
          <MetricCard
            title="Compute Ampere A1 (Arm)"
            subtitle="Instâncias Flex (4 OCPUs / 24 GB)"
            icon={Cpu}
            used={`${computeAmpere.ocpus_allocated || 0} OCPU`}
            limit={`${computeAmpere.limit_ocpus || 4} OCPUs`}
            unit=""
            percentage={((computeAmpere.ocpus_allocated || 0) / (computeAmpere.limit_ocpus || 4)) * 100}
            status={computeAmpere.status}
          >
            <div className="flex justify-between">
              <span>RAM Alocada:</span>
              <span className="text-slate-200 font-medium">
                {computeAmpere.memory_gb_allocated || 0} / {computeAmpere.limit_memory_gb || 24} GB
              </span>
            </div>
            <div className="flex justify-between">
              <span>Instâncias Ativas:</span>
              <span className="text-slate-200 font-medium">{computeAmpere.instances_count || 0}</span>
            </div>
          </MetricCard>

          {/* 3. Compute AMD Micro */}
          <MetricCard
            title="Compute AMD Micro"
            subtitle="Shape VM.Standard.E2.1.Micro"
            icon={Server}
            used={computeMicro.active_instances || 0}
            limit={computeMicro.limit_instances || 2}
            unit="Instâncias"
            percentage={((computeMicro.active_instances || 0) / (computeMicro.limit_instances || 2)) * 100}
            status={computeMicro.status}
          >
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="text-slate-200 font-medium">
                {(computeMicro.active_instances || 0) < 2 ? 'Slots Livres' : 'Limite Atingido'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Permitido:</span>
              <span className="text-slate-200 font-medium">Até 2 VMs gratuitas</span>
            </div>
          </MetricCard>

          {/* 4. Object Storage */}
          <MetricCard
            title="Armazenamento de Objetos"
            subtitle="Tier Standard + Arquivo"
            icon={Database}
            used={objectStorage.standard_gb || 0}
            limit={objectStorage.limit_standard_gb || 10}
            unit="GB"
            percentage={objectStorage.standard_percentage || 0}
            status={objectStorage.status}
          >
            <div className="flex justify-between">
              <span>Tier Arquivo/Infreq.:</span>
              <span className="text-slate-200 font-medium">{objectStorage.archive_gb || 0} / 10 GB</span>
            </div>
            <div className="flex justify-between">
              <span>Total de Buckets:</span>
              <span className="text-slate-200 font-medium">{objectStorage.bucket_count || 0}</span>
            </div>
          </MetricCard>
        </div>

        {/* Burn Rate & Projection Card */}
        <BurnRateCard
          burnRate={burnRate}
          computeAmpere={computeAmpere}
          network={network}
        />

        {/* Detailed Volumes Inventory Table */}
        <VolumesTable volumes={volumes} />
      </main>

      {/* Footer */}
      <footer className="border-t border-[#22272E] py-6 text-center text-xs text-slate-500">
        OCI Always Free Monitor • Desenvolvido para proteção e visibilidade contra custos acidentais.
      </footer>
    </div>
  );
}
