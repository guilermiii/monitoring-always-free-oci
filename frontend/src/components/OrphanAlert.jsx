import React from 'react';
import { AlertTriangle, HardDrive, ArrowRight } from 'lucide-react';

export default function OrphanAlert({ count, wastedGb, onScrollToVolumes }) {
  if (!count || count === 0) {
    return null;
  }

  return (
    <div className="rounded-2xl p-5 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/30 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 shrink-0">
          <AlertTriangle className="w-6 h-6 stroke-[2.5]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-base font-bold text-amber-300">
              Alerta de Desperdício: {count} {count === 1 ? 'Volume Órfão Detectado' : 'Volumes Órfãos Detectados'}
            </h4>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
              {wastedGb} GB Ociosos
            </span>
          </div>
          <p className="text-sm text-slate-300 mt-1 max-w-3xl leading-relaxed">
            Volumes de boot ou bloco que pertenceram a instâncias deletadas ou desanexadas continuam ocupando
            espaço na cota Always Free (200 GB). Exclua ou reaproveite esses volumes para liberar capacidade gratuita.
          </p>
        </div>
      </div>

      <button
        onClick={onScrollToVolumes}
        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-sm transition-all shrink-0 self-start md:self-center shadow-md active:scale-95"
      >
        <HardDrive className="w-4 h-4" />
        <span>Inspecionar Discos</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
