import React from 'react';
import { Flame, Calendar, TrendingUp, AlertOctagon } from 'lucide-react';

export default function BurnRateCard({ burnRate, computeAmpere, network }) {
  if (!burnRate) return null;

  const daysElapsed = burnRate.days_elapsed || 1;
  const daysInMonth = burnRate.days_in_month || 30;
  const daysRemaining = Math.max(daysInMonth - daysElapsed, 0);
  const monthProgressPct = Math.min(Math.round((daysElapsed / daysInMonth) * 100), 100);

  const projectedOcpu = computeAmpere?.projected_ocpu_hours || 0;
  const ocpuLimit = computeAmpere?.monthly_ocpu_hours_limit || 3000;
  const ocpuRisk = projectedOcpu > ocpuLimit;

  const projectedEgress = network?.egress_projected_tb || 0;
  const egressLimit = network?.egress_tb_limit || 10;
  const egressRisk = projectedEgress > egressLimit;

  return (
    <div className="rounded-2xl p-6 bg-white dark:bg-[#161B22] border border-slate-200 dark:border-[#22272E] shadow-sm dark:shadow-lg transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-orange-500/10 text-orange-500 dark:text-orange-400 border border-orange-500/20 shrink-0">
            <Flame className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Projeção Mensal & Taxa de Queima (Burn-Rate)</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Previsão linear de consumo acumulado até o fechamento do ciclo</p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono bg-slate-100 dark:bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700/60 text-slate-700 dark:text-slate-300">
          <Calendar className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
          <span>Dia {daysElapsed} de {daysInMonth} ({daysRemaining} dias restantes)</span>
        </div>
      </div>

      {/* Cycle Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400 mb-1.5">
          <span>Progresso do Ciclo Mensal</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200">{monthProgressPct}% decorrido</span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${monthProgressPct}%` }}
          ></div>
        </div>
      </div>

      {/* Projections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* OCPU-Hours Projection */}
        <div className={`p-4 rounded-xl border ${ocpuRisk ? 'bg-rose-500/10 border-rose-500/30' : 'bg-slate-50 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-slate-500 dark:text-slate-400" />
              Ampere OCPU-Horas
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-md font-semibold ${ocpuRisk ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400' : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'}`}>
              {ocpuRisk ? 'Risco de Custo' : 'Dentro do Teto'}
            </span>
          </div>

          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">{projectedOcpu.toFixed(0)}h</span>
            <span className="text-xs text-slate-500 dark:text-slate-400">projetadas / {ocpuLimit}h cota</span>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400">
            Ritmo diário: <strong className="text-slate-800 dark:text-slate-200">{burnRate.ocpu_burn_rate_daily}h/dia</strong>
          </p>
        </div>

        {/* Egress Projection */}
        <div className={`p-4 rounded-xl border ${egressRisk ? 'bg-rose-500/10 border-rose-500/30' : 'bg-slate-50 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-slate-500 dark:text-slate-400" />
              Tráfego de Saída (Egress)
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-md font-semibold ${egressRisk ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400' : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'}`}>
              {egressRisk ? 'Risco de Custo' : 'Dentro do Teto'}
            </span>
          </div>

          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">{projectedEgress.toFixed(2)} TB</span>
            <span className="text-xs text-slate-500 dark:text-slate-400">projetados / {egressLimit} TB cota</span>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400">
            Ritmo diário: <strong className="text-slate-800 dark:text-slate-200">{burnRate.egress_burn_rate_daily_gb} GB/dia</strong>
          </p>
        </div>
      </div>

      {/* Warnings Banner if any */}
      {burnRate.warnings && burnRate.warnings.length > 0 && (
        <div className="mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-300 text-xs flex items-start gap-2.5">
          <AlertOctagon className="w-4 h-4 shrink-0 text-rose-500 dark:text-rose-400 mt-0.5" />
          <div className="space-y-1">
            {burnRate.warnings.map((w, idx) => (
              <p key={idx}>{w}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
