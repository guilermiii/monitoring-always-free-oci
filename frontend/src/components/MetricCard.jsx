import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export default function MetricCard({
  title,
  icon: Icon,
  used,
  limit,
  unit,
  percentage,
  status = 'safe',
  subtitle,
  children,
}) {
  const getStatusTheme = (s) => {
    switch (s) {
      case 'danger':
        return {
          bar: 'bg-rose-500',
          badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          border: 'border-rose-500/40',
          text: 'text-rose-400',
        };
      case 'warning':
        return {
          bar: 'bg-amber-500',
          badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          border: 'border-amber-500/40',
          text: 'text-amber-400',
        };
      default:
        return {
          bar: 'bg-emerald-500',
          badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          border: 'border-[#22272E]',
          text: 'text-emerald-400',
        };
    }
  };

  const theme = getStatusTheme(status);
  const clampedPct = Math.min(Math.max(percentage || 0, 0), 100);

  return (
    <div className={`p-5 rounded-2xl bg-[#161B22] border ${theme.border} shadow-lg transition-all hover:border-slate-600`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-slate-800 text-slate-200 border border-slate-700/60">
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
            {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
          </div>
        </div>

        <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${theme.badge}`}>
          {clampedPct.toFixed(1)}%
        </span>
      </div>

      {/* Main Consumption Figures */}
      <div className="mb-4">
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold tracking-tight text-white">{used}</span>
          <span className="text-sm text-slate-400">/ {limit} {unit}</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all duration-500 ${theme.bar}`}
          style={{ width: `${clampedPct}%` }}
        ></div>
      </div>

      {/* Slot for custom details or sub-metrics */}
      {children && (
        <div className="pt-3 border-t border-slate-800/80 text-xs text-slate-400 space-y-1.5">
          {children}
        </div>
      )}
    </div>
  );
}
