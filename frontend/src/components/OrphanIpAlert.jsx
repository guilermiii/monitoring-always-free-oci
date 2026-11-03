import React from 'react';
import { AlertCircle, Globe, ArrowRight } from 'lucide-react';

export default function OrphanIpAlert({ count, onScrollToIps }) {
  if (!count || count === 0) return null;

  return (
    <div className="rounded-2xl p-5 bg-gradient-to-r from-rose-500/10 via-rose-500/5 to-transparent border border-rose-500/30 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30 shrink-0">
          <Globe className="w-6 h-6 stroke-[2.5]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-base font-bold text-rose-300">
              Atenção: {count} {count === 1 ? 'IP Fixo Não Vinculado' : 'IPs Fixos Não Vinculados'}
            </h4>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
              IP Reservado Ocioso
            </span>
          </div>
          <p className="text-sm text-slate-300 mt-1 max-w-3xl leading-relaxed">
            Você possui IP(s) público(s) reservado(s) que não estão associados a nenhuma interface de rede (VNIC).
            IPs reservados ociosos consomem sua cota gratuita e podem incorrer em cobranças se a conta for alterada para PAYG.
          </p>
        </div>
      </div>

      <button
        onClick={onScrollToIps}
        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-sm transition-all shrink-0 self-start md:self-center shadow-md active:scale-95"
      >
        <Globe className="w-4 h-4" />
        <span>Ver IPs Públicos</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
