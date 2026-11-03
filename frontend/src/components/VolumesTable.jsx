import React, { useState } from 'react';
import { HardDrive, AlertTriangle, CheckCircle2, Search, Filter } from 'lucide-react';

export default function VolumesTable({ volumes = [] }) {
  const [filterOrphanOnly, setFilterOrphanOnly] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = volumes.filter((vol) => {
    if (filterOrphanOnly && !vol.is_orphan) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchName = vol.display_name?.toLowerCase().includes(term);
      const matchId = vol.id?.toLowerCase().includes(term);
      const matchComp = vol.compartment_name?.toLowerCase().includes(term);
      return matchName || matchId || matchComp;
    }
    return true;
  });

  const orphanCount = volumes.filter((v) => v.is_orphan).length;

  return (
    <div id="volumes-inventory" className="rounded-2xl bg-[#161B22] border border-[#22272E] shadow-lg overflow-hidden">
      {/* Header & Controls */}
      <div className="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-slate-800 text-slate-200 border border-slate-700/60">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Inventário Detalhado de Discos & Volumes</h3>
            <p className="text-xs text-slate-400">Varredura de boot volumes e block volumes em todos os compartimentos</p>
          </div>
        </div>

        {/* Filter and Search */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Buscar por nome ou ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700/80 text-xs text-slate-200 focus:outline-none focus:border-red-500 w-48 sm:w-64"
            />
          </div>

          <button
            onClick={() => setFilterOrphanOnly(!filterOrphanOnly)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
              filterOrphanOnly
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            <span>Apenas Órfãos ({orphanCount})</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-[#12161C] text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider">
            <tr>
              <th className="py-3 px-4">Nome do Volume</th>
              <th className="py-3 px-4">Tipo</th>
              <th className="py-3 px-4">Tamanho</th>
              <th className="py-3 px-4">Compartimento</th>
              <th className="py-3 px-4">Status de Vínculo</th>
              <th className="py-3 px-4">Instância Anexada</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  Nenhum volume encontrado com os filtros aplicados.
                </td>
              </tr>
            ) : (
              filtered.map((vol) => (
                <tr
                  key={vol.id}
                  className={`hover:bg-slate-800/40 transition-colors ${
                    vol.is_orphan ? 'bg-amber-500/[0.03]' : ''
                  }`}
                >
                  <td className="py-3.5 px-4 font-medium text-white max-w-[200px] truncate" title={vol.display_name}>
                    {vol.display_name}
                    <div className="text-[10px] text-slate-500 font-mono truncate" title={vol.id}>
                      {vol.id}
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-medium uppercase ${
                      vol.volume_type === 'boot'
                        ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                        : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    }`}>
                      {vol.volume_type}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-200">
                    {vol.size_in_gbs} GB
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {vol.compartment_name || 'root'}
                  </td>
                  <td className="py-3.5 px-4">
                    {vol.is_orphan ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        Órfão (Desconectado)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        Anexado
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 max-w-[180px] truncate" title={vol.attached_instance_id || 'Nenhuma'}>
                    {vol.attached_instance_id ? (
                      <span className="text-slate-300">{vol.attached_instance_id.slice(-16)}</span>
                    ) : (
                      <span className="text-slate-600 italic">-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
