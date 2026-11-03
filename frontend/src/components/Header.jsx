import React from 'react';
import { RefreshCw, Cloud, CheckCircle, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function Header({ tenancy, collectedAt, isRefreshing, onRefresh, connectionStatus }) {
  const formatTime = (isoString) => {
    if (!isoString) return 'Nunca';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + 
        ' (' + d.toLocaleDateString('pt-BR') + ')';
    } catch {
      return isoString;
    }
  };

  return (
    <header className="border-b border-[#22272E] bg-[#161B22]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Brand & Tenancy Info */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500">
            <Cloud className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">OCI Always Free Monitor</h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Ativo
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span>Tenancy: <strong className="text-slate-200">{tenancy?.name || 'Carregando...'}</strong></span>
              <span>•</span>
              <span>Região: <span className="text-slate-300 font-mono">{tenancy?.home_region || 'us-ashburn-1'}</span></span>
            </div>
          </div>
        </div>

        {/* Sync Controls & Last Update */}
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-xs text-slate-400">Última Coleta</p>
            <p className="text-xs font-medium text-slate-200 font-mono">{formatTime(collectedAt)}</p>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm ${
              isRefreshing
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-red-600 hover:bg-red-500 text-white shadow-red-900/20 hover:shadow-red-900/40 border border-red-500/50 active:scale-95'
            }`}
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Sincronizando...' : 'Sincronizar Agora'}</span>
          </button>
        </div>

      </div>
    </header>
  );
}
