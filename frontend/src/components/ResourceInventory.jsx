import React, { useState } from 'react';
import {
  HardDrive,
  Network,
  Globe,
  SlidersHorizontal,
  Database,
  Search,
  Filter,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';

export default function ResourceInventory({
  volumes = [],
  vcns = [],
  publicIps = [],
  loadBalancers = [],
  databases = [],
  activeTab = 'volumes',
  setActiveTab,
}) {
  const [tab, setTab] = useState(activeTab);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterOrphanVolumes, setFilterOrphanVolumes] = useState(false);
  const [filterUnassignedIps, setFilterUnassignedIps] = useState(false);

  // Sync internal state if parent controls tab
  const currentTab = setActiveTab ? activeTab : tab;
  const changeTab = (t) => {
    if (setActiveTab) setActiveTab(t);
    else setTab(t);
  };

  const term = searchTerm.toLowerCase();

  // Filter logic per tab
  const filteredVolumes = volumes.filter((v) => {
    if (filterOrphanVolumes && !v.is_orphan) return false;
    if (!term) return true;
    return (
      v.display_name?.toLowerCase().includes(term) ||
      v.id?.toLowerCase().includes(term) ||
      v.compartment_name?.toLowerCase().includes(term)
    );
  });

  const filteredVcns = vcns.filter((v) => {
    if (!term) return true;
    return (
      v.display_name?.toLowerCase().includes(term) ||
      v.cidr_block?.toLowerCase().includes(term) ||
      v.id?.toLowerCase().includes(term)
    );
  });

  const filteredIps = publicIps.filter((ip) => {
    if (filterUnassignedIps && !ip.is_unassigned) return false;
    if (!term) return true;
    return (
      ip.ip_address?.toLowerCase().includes(term) ||
      ip.display_name?.toLowerCase().includes(term) ||
      ip.assigned_entity_id?.toLowerCase().includes(term)
    );
  });

  const filteredLbs = loadBalancers.filter((lb) => {
    if (!term) return true;
    return (
      lb.display_name?.toLowerCase().includes(term) ||
      lb.shape_name?.toLowerCase().includes(term) ||
      lb.ip_addresses?.some((ip) => ip.toLowerCase().includes(term))
    );
  });

  const filteredDbs = databases.filter((db) => {
    if (!term) return true;
    return (
      db.display_name?.toLowerCase().includes(term) ||
      db.db_name?.toLowerCase().includes(term) ||
      db.db_workload?.toLowerCase().includes(term)
    );
  });

  const orphanVolumeCount = volumes.filter((v) => v.is_orphan).length;
  const unassignedIpCount = publicIps.filter((ip) => ip.is_unassigned).length;
  const reservedIpCount = publicIps.filter((ip) => ip.lifetime === 'RESERVED').length;
  const ephemeralIpCount = publicIps.filter((ip) => ip.lifetime === 'EPHEMERAL').length;

  return (
    <div id="resource-inventory" className="rounded-2xl bg-[#161B22] border border-[#22272E] shadow-lg overflow-hidden">
      {/* Header with Tab Navigation */}
      <div className="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-white">Inventário de Recursos OCI</h3>
          <p className="text-xs text-slate-400">Detalhamento dos recursos em todos os compartimentos</p>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Buscar por nome, IP ou ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-xs text-slate-200 focus:outline-none focus:border-red-500 w-full sm:w-64"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-1 px-5 pt-3 border-b border-slate-800/80 bg-[#12161C]">
        <button
          onClick={() => changeTab('volumes')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 ${
            currentTab === 'volumes'
              ? 'text-white border-red-500 bg-[#161B22]'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          <HardDrive className="w-3.5 h-3.5" />
          <span>Discos & Volumes ({volumes.length})</span>
          {orphanVolumeCount > 0 && (
            <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-amber-500/20 text-amber-300 font-bold">
              {orphanVolumeCount}
            </span>
          )}
        </button>

        <button
          onClick={() => changeTab('vcns')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 ${
            currentTab === 'vcns'
              ? 'text-white border-red-500 bg-[#161B22]'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          <Network className="w-3.5 h-3.5" />
          <span>VCNs & Redes ({vcns.length})</span>
        </button>

        <button
          onClick={() => changeTab('ips')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 ${
            currentTab === 'ips'
              ? 'text-white border-red-500 bg-[#161B22]'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          <span>IPs Públicos ({publicIps.length})</span>
          {unassignedIpCount > 0 && (
            <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-rose-500/20 text-rose-300 font-bold">
              {unassignedIpCount}
            </span>
          )}
        </button>

        <button
          onClick={() => changeTab('lbs')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 ${
            currentTab === 'lbs'
              ? 'text-white border-red-500 bg-[#161B22]'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Load Balancers ({loadBalancers.length})</span>
        </button>

        <button
          onClick={() => changeTab('dbs')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 ${
            currentTab === 'dbs'
              ? 'text-white border-red-500 bg-[#161B22]'
              : 'text-slate-400 border-transparent hover:text-slate-200'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>Bancos Autônomos ({databases.length})</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="overflow-x-auto">
        {/* 1. Volumes Tab */}
        {currentTab === 'volumes' && (
          <div>
            <div className="px-5 py-2.5 bg-slate-900/40 flex justify-between items-center text-xs text-slate-400 border-b border-slate-800">
              <span>Listando Boot Volumes e Block Volumes ativos</span>
              <button
                onClick={() => setFilterOrphanVolumes(!filterOrphanVolumes)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border ${
                  filterOrphanVolumes
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                <Filter className="w-3 h-3" />
                <span>Apenas Órfãos ({orphanVolumeCount})</span>
              </button>
            </div>

            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-[#12161C] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Nome do Volume</th>
                  <th className="py-3 px-4">Tipo</th>
                  <th className="py-3 px-4">Tamanho</th>
                  <th className="py-3 px-4">Compartimento</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Instância</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {filteredVolumes.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      Nenhum volume ativo encontrado.
                    </td>
                  </tr>
                ) : (
                  filteredVolumes.map((vol) => (
                    <tr key={vol.id} className={`hover:bg-slate-800/40 ${vol.is_orphan ? 'bg-amber-500/[0.03]' : ''}`}>
                      <td className="py-3.5 px-4 font-medium text-white max-w-[200px] truncate" title={vol.display_name}>
                        {vol.display_name}
                        <div className="text-[10px] text-slate-500 font-mono truncate">{vol.id}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium uppercase ${
                          vol.volume_type === 'boot' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                        }`}>
                          {vol.volume_type}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-200">{vol.size_in_gbs} GB</td>
                      <td className="py-3.5 px-4 text-slate-400">{vol.compartment_name || 'root'}</td>
                      <td className="py-3.5 px-4">
                        {vol.is_orphan ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                            Órfão
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            Anexado
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 max-w-[160px] truncate">
                        {vol.attached_instance_id ? vol.attached_instance_id.slice(-16) : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* 2. VCNs Tab */}
        {currentTab === 'vcns' && (
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#12161C] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Nome da VCN</th>
                <th className="py-3 px-4">Bloco CIDR</th>
                <th className="py-3 px-4">Compartimento</th>
                <th className="py-3 px-4">Estado</th>
                <th className="py-3 px-4">Criado em</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredVcns.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    Nenhuma VCN ativa encontrada (limite gratuito: até 2 VCNs).
                  </td>
                </tr>
              ) : (
                filteredVcns.map((vcn) => (
                  <tr key={vcn.id} className="hover:bg-slate-800/40">
                    <td className="py-3.5 px-4 font-medium text-white max-w-[220px] truncate" title={vcn.display_name}>
                      {vcn.display_name}
                      <div className="text-[10px] text-slate-500 font-mono truncate">{vcn.id}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-cyan-400 font-semibold">{vcn.cidr_block || 'N/A'}</td>
                    <td className="py-3.5 px-4 text-slate-400">{vcn.compartment_name || 'root'}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        {vcn.lifecycle_state}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">{vcn.time_created || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* 3. Public IPs Tab */}
        {currentTab === 'ips' && (
          <div>
            <div className="px-5 py-2.5 bg-slate-900/40 flex flex-wrap justify-between items-center gap-2 text-xs text-slate-400 border-b border-slate-800">
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                <span className="font-medium text-slate-300">IPs Públicos:</span>
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                  Fixos Reservados: {reservedIpCount} / 1
                </span>
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[11px] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                  Efêmeros: {ephemeralIpCount}
                </span>
              </div>
              <button
                onClick={() => setFilterUnassignedIps(!filterUnassignedIps)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border ${
                  filterUnassignedIps
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                <Filter className="w-3 h-3" />
                <span>Apenas Não Vinculados ({unassignedIpCount})</span>
              </button>
            </div>

            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-[#12161C] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Endereço IP</th>
                  <th className="py-3 px-4">Tipo</th>
                  <th className="py-3 px-4">Nome</th>
                  <th className="py-3 px-4">Vínculo</th>
                  <th className="py-3 px-4">VNIC Associada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {filteredIps.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      Nenhum IP público ativo encontrado (limite gratuito: 1 IP Fixo Reservado).
                    </td>
                  </tr>
                ) : (
                  filteredIps.map((ip) => (
                    <tr key={ip.id} className={`hover:bg-slate-800/40 ${ip.is_unassigned ? 'bg-rose-500/[0.04]' : ''}`}>
                      <td className="py-3.5 px-4 font-mono font-bold text-white">{ip.ip_address}</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                          ip.lifetime === 'RESERVED'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                        }`}>
                          {ip.lifetime === 'RESERVED' ? 'Fixo / Reservado' : 'Efêmero'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">{ip.display_name}</td>
                      <td className="py-3.5 px-4">
                        {ip.is_unassigned ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">
                            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                            Não Vinculado (Ocioso)
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            Vinculado
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 max-w-[160px] truncate">
                        {ip.assigned_entity_id ? ip.assigned_entity_id.slice(-16) : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* 4. Load Balancers Tab */}
        {currentTab === 'lbs' && (
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#12161C] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Nome do Load Balancer</th>
                <th className="py-3 px-4">Tipo</th>
                <th className="py-3 px-4">Shape / Largura de Banda</th>
                <th className="py-3 px-4">Endereços IP</th>
                <th className="py-3 px-4">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredLbs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    Nenhum Load Balancer ativo encontrado (limite gratuito: 1 Flexible LB de 10 Mbps + 1 NLB).
                  </td>
                </tr>
              ) : (
                filteredLbs.map((lb) => (
                  <tr key={lb.id} className="hover:bg-slate-800/40">
                    <td className="py-3.5 px-4 font-medium text-white max-w-[220px] truncate" title={lb.display_name}>
                      {lb.display_name}
                      <div className="text-[10px] text-slate-500 font-mono truncate">{lb.id}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                        lb.lb_type === 'flexible'
                          ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                      }`}>
                        {lb.lb_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-200">{lb.shape_name}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {lb.ip_addresses?.join(', ') || '-'}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        {lb.lifecycle_state}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* 5. Autonomous Databases Tab */}
        {currentTab === 'dbs' && (
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#12161C] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Nome do Banco</th>
                <th className="py-3 px-4">Database Name</th>
                <th className="py-3 px-4">Workload</th>
                <th className="py-3 px-4">Armazenamento</th>
                <th className="py-3 px-4">OCPUs</th>
                <th className="py-3 px-4">Always Free</th>
                <th className="py-3 px-4">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredDbs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Nenhum banco autônomo Always Free encontrado (limite gratuito: até 2 instâncias / 40 GB).
                  </td>
                </tr>
              ) : (
                filteredDbs.map((db) => (
                  <tr key={db.id} className="hover:bg-slate-800/40">
                    <td className="py-3.5 px-4 font-medium text-white max-w-[200px] truncate" title={db.display_name}>
                      {db.display_name}
                      <div className="text-[10px] text-slate-500 font-mono truncate">{db.id}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-200">{db.db_name}</td>
                    <td className="py-3.5 px-4 uppercase text-[11px] text-slate-300">{db.db_workload}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-200">{db.data_storage_size_in_gbs} GB</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-200">{db.cpu_core_count} OCPU</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Sim
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        {db.lifecycle_state}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
