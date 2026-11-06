import React from 'react';
import {
  RefreshCw,
  Cloud,
  Activity,
  CheckCircle,
  AlertTriangle,
  ShieldCheck,
  Lock,
  LogOut,
  Eye,
  Sun,
  Moon,
} from 'lucide-react';

export default function Header({
  tenancy,
  collectedAt,
  apiUsage,
  isRefreshing,
  onRefresh,
  isAdmin,
  user,
  onLogout,
  onOpenLogin,
  theme = 'light',
  onToggleTheme,
}) {
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

  const getStatusBadge = (status) => {
    switch (status) {
      case 'danger':
        return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
      case 'warning':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
      default:
        return 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border-cyan-500/20';
    }
  };

  return (
    <header className="border-b border-slate-200 dark:border-[#22272E] bg-white/85 dark:bg-[#161B22]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4 transition-colors">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Brand & Tenancy Info */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 shrink-0">
            <Cloud className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">OCI Always Free Monitor</h1>
              
              {/* Cluster Cloud Badge */}
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse"></span>
                Ativo
              </span>

              {/* Mode Badge (Admin vs Portfolio Guest) */}
              {isAdmin ? (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
                  Admin: {user || 'admin'}
                </span>
              ) : (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 flex items-center gap-1.5" title="Visualização pública em modo portfólio (dados protegidos)">
                  <Eye className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
                  Portfólio (Leitura)
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
              <span>Tenancy: <strong className="text-slate-800 dark:text-slate-200">{tenancy?.name || 'Carregando...'}</strong></span>
              <span>•</span>
              <span>Região: <span className="text-slate-700 dark:text-slate-300 font-mono">{tenancy?.home_region || 'us-ashburn-1'}</span></span>
            </div>
          </div>
        </div>

        {/* Sync Controls, API Quota & Last Update */}
        <div className="flex items-center gap-3 flex-wrap sm:flex-nowrap justify-end">
          
          {/* OCI API Calls Quota Widget */}
          {apiUsage && (
            <div
              className="text-right hidden sm:block bg-slate-100 dark:bg-[#0D1117]/80 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-[#30363D]"
              title={`Consumo diário de chamadas de API da OCI: ${apiUsage.calls_today.toLocaleString('pt-BR')} realizadas de ${apiUsage.daily_limit.toLocaleString('pt-BR')} permitidas (${apiUsage.percentage}%). Limite de taxa da OCI: 3.000 req/min.`}
            >
              <div className="flex items-center justify-end gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                <Activity className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                <span>Cota de API (Hoje)</span>
                <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-medium border ${getStatusBadge(apiUsage.status)}`}>
                  {apiUsage.percentage}%
                </span>
              </div>
              <div className="flex items-baseline justify-end gap-1 font-mono text-xs mt-0.5">
                <span className="font-bold text-slate-900 dark:text-slate-100">{apiUsage.calls_today.toLocaleString('pt-BR')}</span>
                <span className="text-slate-400 dark:text-slate-500">/</span>
                <span className="text-slate-600 dark:text-slate-400">{apiUsage.daily_limit.toLocaleString('pt-BR')}</span>
                <span className="text-[10px] text-slate-500 ml-1 hidden lg:inline">
                  ({apiUsage.calls_last_run} na varredura)
                </span>
              </div>
            </div>
          )}

          {/* Last Update */}
          <div className="text-right hidden sm:block">
            <p className="text-xs text-slate-500 dark:text-slate-400">Última Coleta</p>
            <p className="text-xs font-medium text-slate-800 dark:text-slate-200 font-mono">{formatTime(collectedAt)}</p>
          </div>

          {/* Accessibility: Theme Toggle Button */}
          <button
            onClick={onToggleTheme}
            className="flex items-center justify-center p-2 rounded-lg text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-[#0D1117] dark:hover:bg-slate-800 border border-slate-200 dark:border-[#30363D] transition-all"
            title={theme === 'dark' ? 'Alternar para tema claro' : 'Alternar para tema escuro'}
            aria-label={theme === 'dark' ? 'Alternar para tema claro' : 'Alternar para tema escuro'}
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-700" />
            )}
          </button>

          {/* Admin Login / Logout Action */}
          {isAdmin ? (
            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-[#0D1117] dark:hover:bg-slate-800 border border-slate-200 dark:border-[#30363D] transition-all"
              title="Encerrar sessão administrativa"
            >
              <LogOut className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
              <span>Sair</span>
            </button>
          ) : (
            <button
              onClick={onOpenLogin}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-[#0D1117] dark:hover:bg-slate-800 border border-slate-200 dark:border-[#30363D] transition-all"
              title="Acesso exclusivo para o proprietário"
            >
              <Lock className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
              <span>Login Admin</span>
            </button>
          )}

          {/* Sync Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm ${
              isRefreshing
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-300 dark:border-slate-700'
                : 'bg-red-600 hover:bg-red-500 text-white shadow-red-900/20 hover:shadow-red-900/40 border border-red-500/50 active:scale-95'
            }`}
            title={isAdmin ? "Forçar varredura imediata na OCI" : "A sincronização sob demanda requer login de administrador"}
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Sincronizando...' : 'Sincronizar Agora'}</span>
          </button>
        </div>

      </div>
    </header>
  );
}

