import React, { useState, useEffect } from 'react';
import {
  HardDrive,
  Cpu,
  Server,
  Database,
  Network,
  Globe,
  SlidersHorizontal,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  ShieldAlert,
  Lock,
} from 'lucide-react';
import Header from './components/Header';
import MetricCard from './components/MetricCard';
import OrphanAlert from './components/OrphanAlert';
import OrphanIpAlert from './components/OrphanIpAlert';
import BurnRateCard from './components/BurnRateCard';
import ResourceInventory from './components/ResourceInventory';
import LoginModal from './components/LoginModal';
import LockScreen from './components/LockScreen';
import { AuthProvider, useAuth } from './context/AuthContext';

function Dashboard() {
  const { isAdmin, user, logout } = useAuth();
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') || 'light';
    }
    return 'light';
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try {
      localStorage.setItem('theme', theme);
    } catch (e) {}
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const [viewMode, setViewMode] = useState(() => {
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/portfolio')) {
      return 'portfolio';
    }
    return 'gate';
  });
  const [summary, setSummary] = useState(null);
  const [instances, setInstances] = useState([]);
  const [volumes, setVolumes] = useState([]);
  const [networkInv, setNetworkInv] = useState({ vcns: [], public_ips: [], unassigned_ips: [], load_balancers: [] });
  const [databaseInv, setDatabaseInv] = useState([]);
  const [activeTab, setActiveTab] = useState('instances');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [syncWarning, setSyncWarning] = useState(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [sumRes, volRes, netRes, dbRes, instRes] = await Promise.all([
        fetch('/api/v1/summary'),
        fetch('/api/v1/storage/volumes'),
        fetch('/api/v1/network/inventory'),
        fetch('/api/v1/database/inventory'),
        fetch('/api/v1/compute/instances'),
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
      if (netRes.ok) {
        const netData = await netRes.json();
        setNetworkInv(netData);
      }
      if (dbRes.ok) {
        const dbData = await dbRes.json();
        setDatabaseInv(dbData);
      }
      if (instRes.ok) {
        const instData = await instRes.json();
        setInstances(instData);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Falha ao conectar à API');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleSyncClick = async () => {
    if (!isAdmin) {
      setSyncWarning(
        'A sincronização direta contra as APIs da Oracle Cloud é restrita ao administrador para proteger as cotas da nuvem. O dashboard é atualizado automaticamente a cada 10 minutos.'
      );
      setIsLoginModalOpen(true);
      return;
    }

    setRefreshing(true);
    setSyncWarning(null);
    try {
      const res = await fetch('/api/v1/refresh', { method: 'POST' });
      if (!res.ok) {
        if (res.status === 401) {
          setIsLoginModalOpen(true);
          throw new Error('Sessão expirada. Faça login novamente.');
        }
        throw new Error('Falha na sincronização imediata');
      }
      await fetchData();
    } catch (err) {
      console.error(err);
      setError(err.message);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [isAdmin]);

  const scrollToSection = (tabName) => {
    setActiveTab(tabName);
    const el = document.getElementById('resource-inventory');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleLogout = async () => {
    await logout();
    setViewMode('gate');
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', '/');
    }
  };

  // Se o usuário não for administrador e a rota for a tela de bloqueio, exibe a Trava de Acesso
  if (!isAdmin && viewMode === 'gate') {
    return (
      <LockScreen
        onEnterPortfolio={() => {
          setViewMode('portfolio');
          if (typeof window !== 'undefined') {
            window.history.pushState({}, '', '/portfolio');
          }
        }}
      />
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0D1117] flex flex-col items-center justify-center text-slate-400 gap-4">
        <RefreshCw className="w-8 h-8 text-red-500 animate-spin" />
        <p className="text-sm font-medium">Carregando métricas da Oracle Cloud...</p>
      </div>
    );
  }

  // Quotas & Metrics extraction
  const blockStorage = summary?.storage?.block_storage || {};
  const objectStorage = summary?.storage?.object_storage || {};
  const computeAmpere = summary?.compute?.ampere_a1 || {};
  const computeMicro = summary?.compute?.amd_micro || {};
  const networking = summary?.networking || {};
  const vcn = networking.vcn || { active_vcns: 0, limit_vcns: 2, percentage: 0, status: 'safe' };
  const publicIp = networking.public_ip || { reserved_count: 0, reserved_limit: 1, unassigned_reserved_count: 0, ephemeral_count: 0, total_active_ips: 0, percentage: 0, status: 'safe' };
  const loadBalancer = networking.load_balancer || { flexible_lb_count: 0, limit_flexible_lb: 1, nlb_count: 0, limit_nlb: 1, status: 'safe' };
  const bastion = networking.bastion || { active_bastions: 0, limit_bastions: 2, percentage: 0, status: 'safe' };
  const database = summary?.database?.autonomous_database || { active_count: 0, limit_count: 2, allocated_storage_gb: 0, limit_storage_gb: 40, percentage: 0, status: 'safe' };
  const burnRate = summary?.burn_rate || {};
  const network = summary?.network || {};

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0D1117] text-slate-800 dark:text-slate-100 flex flex-col selection:bg-red-500 selection:text-white transition-colors duration-200">
      <Header
        tenancy={summary?.tenancy}
        collectedAt={summary?.collected_at}
        apiUsage={summary?.api_usage}
        isRefreshing={refreshing}
        onRefresh={handleSyncClick}
        isAdmin={isAdmin}
        user={user}
        onLogout={handleLogout}
        onOpenLogin={() => {
          setSyncWarning(null);
          setIsLoginModalOpen(true);
        }}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />

      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8 flex-1">
        {/* Portfolio Mode Notice Banner for Visitors */}
        {!isAdmin && (
          <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-700 dark:text-indigo-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-3">
              <ShieldAlert className="w-5 h-5 text-indigo-500 dark:text-indigo-400 shrink-0" />
              <span>
                <strong>Modo Portfólio (Cluster Kubernetes ARM):</strong> Os dados de infraestrutura, OCIDs e identificadores foram anonimizados para proteção contra ataques. O coletor assíncrono atualiza o cache automaticamente a cada 10 minutos.
              </span>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
              <button
                onClick={() => {
                  setViewMode('gate');
                  if (typeof window !== 'undefined') window.history.pushState({}, '', '/');
                }}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
              >
                Voltar à Trava
              </button>
              <button
                onClick={() => {
                  setSyncWarning(null);
                  setIsLoginModalOpen(true);
                }}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-700 dark:text-indigo-200 flex items-center gap-1.5 transition-colors"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Login Admin</span>
              </button>
            </div>
          </div>
        )}

        {/* Error notification if any */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-500 dark:text-rose-400" />
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

        {/* Alerts Section */}
        <div className="space-y-4">
          <OrphanAlert
            count={blockStorage.orphan_volumes_count}
            wastedGb={blockStorage.orphan_wasted_gb}
            onScrollToVolumes={() => scrollToSection('volumes')}
          />

          <OrphanIpAlert
            count={publicIp.unassigned_reserved_count}
            onScrollToIps={() => scrollToSection('ips')}
          />
        </div>

        {/* 1. SEÇÃO: Projeção Mensal & Taxa de Queima (Primeira Fileira Isolada) */}
        <div className="w-full">
          <BurnRateCard
            burnRate={burnRate}
            computeAmpere={computeAmpere}
            network={network}
          />
        </div>

        {/* 2. SEÇÃO: Compute & Armazenamento */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Compute & Armazenamento
            </h2>
            <span className="text-xs text-slate-500">Ampere A1 • AMD Micro • Block & Object Storage</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Block Storage */}
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
                <span className="text-slate-800 dark:text-slate-200 font-medium">{blockStorage.boot_volumes_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Block Volumes:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">{blockStorage.block_volumes_count || 0}</span>
              </div>
              {blockStorage.orphan_volumes_count > 0 && (
                <div className="flex justify-between text-amber-600 dark:text-amber-400 font-medium">
                  <span>Discos Órfãos:</span>
                  <span>{blockStorage.orphan_volumes_count} ({blockStorage.orphan_wasted_gb} GB)</span>
                </div>
              )}
            </MetricCard>

            {/* Compute Ampere A1 (Arm) */}
            <MetricCard
              title="Compute Ampere A1 (Arm)"
              subtitle={"Instâncias Flex\n(4 OCPUs / 24 GB)"}
              icon={Cpu}
              percentage={Math.max(
                ((computeAmpere.ocpus_allocated || 0) / (computeAmpere.limit_ocpus || 4)) * 100,
                ((computeAmpere.memory_gb_allocated || 0) / (computeAmpere.limit_memory_gb || 24)) * 100
              )}
              status={computeAmpere.status}
              dualBars={[
                {
                  label: 'CPU (OCPUs)',
                  used: `${computeAmpere.ocpus_allocated || 0} OCPU`,
                  limit: `${computeAmpere.limit_ocpus || 4} OCPUs`,
                  percentage: ((computeAmpere.ocpus_allocated || 0) / (computeAmpere.limit_ocpus || 4)) * 100,
                  barColor: ((computeAmpere.ocpus_allocated || 0) / (computeAmpere.limit_ocpus || 4)) >= 0.9 ? 'bg-rose-500' : 'bg-emerald-500',
                },
                {
                  label: 'Memória RAM',
                  used: `${computeAmpere.memory_gb_allocated || 0} GB`,
                  limit: `${computeAmpere.limit_memory_gb || 24} GB`,
                  percentage: ((computeAmpere.memory_gb_allocated || 0) / (computeAmpere.limit_memory_gb || 24)) * 100,
                  barColor: ((computeAmpere.memory_gb_allocated || 0) / (computeAmpere.limit_memory_gb || 24)) >= 0.9 ? 'bg-rose-500' : 'bg-emerald-500',
                },
              ]}
            >
              <div className="flex justify-between">
                <span>Status:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">
                  {((computeAmpere.ocpus_allocated || 0) < 4 && (computeAmpere.memory_gb_allocated || 0) < 24) ? 'Slots Livres' : 'Limite Atingido'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Permitido:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">Até 4 OCPUs / 24 GB gratuitos</span>
              </div>
              <div className="flex justify-between">
                <span>Instâncias Ativas:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">{computeAmpere.instances_count || 0}</span>
              </div>
            </MetricCard>

            {/* Compute AMD Micro */}
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
                <span className="text-slate-800 dark:text-slate-200 font-medium">
                  {(computeMicro.active_instances || 0) < 2 ? 'Slots Livres' : 'Limite Atingido'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Permitido:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">Até 2 VMs gratuitas</span>
              </div>
            </MetricCard>

            {/* Object Storage */}
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
                <span className="text-slate-800 dark:text-slate-200 font-medium">{objectStorage.archive_gb || 0} / 10 GB</span>
              </div>
              <div className="flex justify-between">
                <span>Total de Buckets:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">{objectStorage.bucket_count || 0}</span>
              </div>
            </MetricCard>
          </div>
        </div>

        {/* 3. SEÇÃO: Rede & Conectividade Always Free */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              Rede & Conectividade Always Free
            </h2>
            <span className="text-xs text-slate-500">VCNs • IP Fixo Reservado • Load Balancer • Bastion</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* VCNs */}
            <MetricCard
              title="Virtual Cloud Networks (VCN)"
              subtitle="Redes Virtuais Isoladas"
              icon={Network}
              used={vcn.active_vcns || 0}
              limit={vcn.limit_vcns || 2}
              unit="VCNs"
              percentage={vcn.percentage || 0}
              status={vcn.status}
            >
              <div className="flex justify-between">
                <span>Permitido:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">Até 2 VCNs gratuitas</span>
              </div>
              <div className="flex justify-between">
                <span>Sub-redes IPv4/IPv6:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">Inclusas</span>
              </div>
            </MetricCard>

            {/* Public IPs: Fixos & Efêmeros */}
            <MetricCard
              title="IPs Públicos (Fixos & Efêmeros)"
              subtitle="1 IP Fixo Always Free + Efêmeros"
              icon={Globe}
              used={publicIp.reserved_count || 0}
              limit={`${publicIp.reserved_limit || 1} Fixo`}
              unit={(publicIp.ephemeral_count || 0) > 0 ? `(+${publicIp.ephemeral_count} efêmero${publicIp.ephemeral_count > 1 ? 's' : ''})` : 'Reservado'}
              percentage={publicIp.percentage || 0}
              status={publicIp.status}
            >
              {/* Mini cards lado a lado */}
              <div className="grid grid-cols-2 gap-2 pb-1">
                <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    <span>IP Fixo Reservado</span>
                  </div>
                  <div className="mt-1 flex items-baseline gap-1 font-mono">
                    <span className="text-base font-bold text-slate-900 dark:text-white">{publicIp.reserved_count || 0}</span>
                    <span className="text-xs text-slate-500">/ {publicIp.reserved_limit || 1}</span>
                    <span className="text-[10px] text-amber-600 dark:text-amber-400/90 ml-auto font-sans">Gratuito</span>
                  </div>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400">
                    <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                    <span>IPs Efêmeros</span>
                  </div>
                  <div className="mt-1 flex items-baseline gap-1 font-mono">
                    <span className="text-base font-bold text-cyan-600 dark:text-cyan-300">{publicIp.ephemeral_count || 0}</span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 ml-auto font-sans">Em uso</span>
                  </div>
                </div>
              </div>

              {/* Total & Vínculo */}
              <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-200 dark:border-slate-800/60">
                <span className="text-slate-600 dark:text-slate-400">Total de IPs Ativos:</span>
                <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                  {(publicIp.reserved_count || 0) + (publicIp.ephemeral_count || 0)}
                </span>
              </div>

              {publicIp.unassigned_reserved_count > 0 ? (
                <div className="flex justify-between items-center text-rose-600 dark:text-rose-400 font-semibold bg-rose-500/10 px-2 py-1 rounded border border-rose-500/20 text-xs">
                  <span>IP Fixo Ocioso:</span>
                  <span>{publicIp.unassigned_reserved_count} Desvinculado</span>
                </div>
              ) : (
                <div className="flex justify-between items-center text-emerald-600 dark:text-emerald-400 text-xs">
                  <span>Status de Vínculo:</span>
                  <span>Todos Vinculados</span>
                </div>
              )}
            </MetricCard>

            {/* Load Balancers */}
            <MetricCard
              title="Load Balancers"
              subtitle="App Flexible LB + NLB"
              icon={SlidersHorizontal}
              used={(loadBalancer.flexible_lb_count || 0) + (loadBalancer.nlb_count || 0)}
              limit="2 (1 ALB + 1 NLB)"
              unit="LBs"
              percentage={(((loadBalancer.flexible_lb_count || 0) + (loadBalancer.nlb_count || 0)) / 2) * 100}
              status={loadBalancer.status}
            >
              <div className="flex justify-between">
                <span>Flexible LB (10 Mbps):</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">{loadBalancer.flexible_lb_count || 0} / 1</span>
              </div>
              <div className="flex justify-between">
                <span>Network LB (NLB):</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">{loadBalancer.nlb_count || 0} / 1</span>
              </div>
            </MetricCard>

            {/* Bastion Service */}
            <MetricCard
              title="OCI Bastion Service"
              subtitle="Acesso Seguro Privado"
              icon={ShieldCheck}
              used={bastion.active_bastions || 0}
              limit={bastion.limit_bastions || 2}
              unit="Bastions"
              percentage={bastion.percentage || 0}
              status={bastion.status}
            >
              <div className="flex justify-between">
                <span>Permitido:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">Até 2 Bastions gratuitos</span>
              </div>
              <div className="flex justify-between">
                <span>Sessões SSH Port-Forward:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">Inclusas</span>
              </div>
            </MetricCard>
          </div>
        </div>

        {/* 4. SEÇÃO: Bancos de Dados Always Free */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500"></span>
              Bancos de Dados Always Free
            </h2>
            <span className="text-xs text-slate-500">Autonomous Database (ATP/ADW) • APEX • 2 DBs / 40 GB</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Autonomous Database */}
            <MetricCard
              title="Autonomous Database"
              subtitle="ATP, ADW, JSON ou APEX"
              icon={Database}
              used={`${database.active_count || 0} DB`}
              limit={`${database.limit_count || 2} Bancos`}
              unit=""
              percentage={database.percentage || 0}
              status={database.status}
            >
              <div className="flex justify-between">
                <span>Armazenamento Alocado:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">
                  {database.allocated_storage_gb || 0} / {database.limit_storage_gb || 40} GB
                </span>
              </div>
              <div className="flex justify-between">
                <span>OCPUs por Banco:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">1 OCPU (Automático)</span>
              </div>
              <div className="flex justify-between">
                <span>Recursos:</span>
                <span className="text-slate-800 dark:text-slate-200 font-medium">APEX + Machine Learning</span>
              </div>
            </MetricCard>
          </div>
        </div>

        {/* 5. SEÇÃO: Inventário Detalhado em Abas */}
        <ResourceInventory
          instances={instances}
          volumes={volumes}
          vcns={networkInv.vcns || []}
          publicIps={networkInv.public_ips || []}
          loadBalancers={networkInv.load_balancers || []}
          databases={databaseInv || []}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
      </main>

      {/* Login Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSuccess={() => fetchData()}
      />

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-[#22272E] py-6 text-center text-xs text-slate-500 transition-colors">
        OCI Always Free Monitor • Visibilidade completa de Compute, Armazenamento, Rede e Bancos de Dados.
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}
