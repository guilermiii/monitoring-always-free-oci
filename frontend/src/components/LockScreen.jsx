import React, { useState } from 'react';
import { Cloud, Lock, Eye, ShieldCheck, ArrowRight, RefreshCw, AlertCircle, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LockScreen({ onEnterPortfolio }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      setError(err.message || 'Credenciais inválidas.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0D1117] flex flex-col justify-between text-slate-100 selection:bg-red-500 selection:text-white px-4 py-8">
      {/* Top Brand Bar */}
      <div className="max-w-5xl w-full mx-auto flex items-center justify-between pb-6 border-b border-[#22272E]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500">
            <Cloud className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              OCI Always Free Monitor
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                K8s ARM Cloud
              </span>
            </h1>
            <p className="text-xs text-slate-400">Controle de Acesso & Portfólio Always Free</p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Ambiente Protegido</span>
        </div>
      </div>

      {/* Main Gate Cards */}
      <div className="max-w-4xl w-full mx-auto py-12">
        <div className="text-center space-y-3 mb-10">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Bem-vindo ao OCI Always Free Monitor
          </h2>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Selecione como deseja acessar o sistema. O painel administrativo é restrito ao proprietário, e o modo portfólio está disponível para demonstração pública com dados protegidos.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Acesso Administrativo (Trava / Login) */}
          <div className="p-6 rounded-2xl bg-[#161B22] border border-[#30363D] shadow-xl flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 to-rose-600"></div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
                  <Lock className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                  Privado
                </span>
              </div>

              <div>
                <h3 className="text-lg font-bold text-white">Acesso Administrativo</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Acesso total ao proprietário: dados reais da tenancy sem máscaras e sincronização manual sob demanda.
                </p>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Usuário</label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#0D1117] border border-[#30363D] text-slate-200 text-sm focus:outline-none focus:border-red-500/60 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Senha</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#0D1117] border border-[#30363D] text-slate-200 text-sm focus:outline-none focus:border-red-500/60 transition-colors"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all shadow-lg shadow-red-900/20 border border-red-500/50 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Validando Acesso...</span>
                    </>
                  ) : (
                    <>
                      <span>Destravar Painel Admin</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>

            <p className="text-[11px] text-slate-500 text-center mt-4">
              Protegido com bcrypt e mitigação de força bruta.
            </p>
          </div>

          {/* Card 2: Modo Portfólio (Demonstração Pública) */}
          <div className="p-6 rounded-2xl bg-[#161B22] border border-[#30363D] shadow-xl flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-indigo-600"></div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
                  <Eye className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Público
                </span>
              </div>

              <div>
                <h3 className="text-lg font-bold text-white">Visualizar Portfólio</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Ambiente de demonstração pública com dados 100% anonimizados, proteção contra flooding e telemetria Always Free em tempo real.
                </p>
              </div>

              <div className="space-y-2.5 pt-2">
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>OCIDs, nomes e IPs ofuscados com segurança</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Cota de API persistente com proteção anti-flooding</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Gráficos de burn-rate e inventário interativo</span>
                </div>
              </div>
            </div>

            <div className="pt-6">
              <button
                type="button"
                onClick={onEnterPortfolio}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-blue-900/20 border border-blue-500/40"
              >
                <Sparkles className="w-4 h-4" />
                <span>Explorar Modo Portfólio</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <p className="text-[11px] text-slate-500 text-center mt-4">
                Atualização em segundo plano a cada 10 minutos.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="max-w-5xl w-full mx-auto pt-6 border-t border-[#22272E] text-center text-xs text-slate-500">
        OCI Always Free Monitor • Cluster Kubernetes ARM Ampere A1 • Arquitetura Segura Cloud-Native
      </footer>
    </div>
  );
}
