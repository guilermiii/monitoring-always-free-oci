import React from 'react';

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
  dualBars,
}) {
  const getStatusTheme = (s) => {
    switch (s) {
      case 'danger':
        return {
          bar: 'bg-rose-500',
          badge: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30',
          border: 'border-rose-500/40',
          text: 'text-rose-600 dark:text-rose-400',
        };
      case 'warning':
        return {
          bar: 'bg-amber-500',
          badge: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
          border: 'border-amber-500/40',
          text: 'text-amber-600 dark:text-amber-400',
        };
      default:
        return {
          bar: 'bg-emerald-500',
          badge: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
          border: 'border-slate-200 dark:border-[#22272E]',
          text: 'text-emerald-600 dark:text-emerald-400',
        };
    }
  };

  const theme = getStatusTheme(status);
  const clampedPct = Math.min(Math.max(percentage || 0, 0), 100);

  return (
    <div className={`p-5 rounded-2xl bg-white dark:bg-[#161B22] border ${theme.border} shadow-sm dark:shadow-lg transition-all hover:border-slate-400 dark:hover:border-slate-600 flex flex-col justify-between`}>
      <div>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-3 min-w-0">
            <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700/60 shrink-0">
              <Icon className="w-5 h-5" />
            </div>
            <div className="min-w-0 flex flex-col justify-center min-h-[44px]">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-200 leading-snug">{title}</h3>
              {subtitle && (
                <p className="text-xs text-slate-500 dark:text-slate-400 whitespace-pre-line leading-relaxed mt-0.5">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          <span className={`text-xs px-2.5 py-1 rounded-full font-medium border shrink-0 ${theme.badge}`}>
            {clampedPct.toFixed(1)}%
          </span>
        </div>

        {/* Dual Bars or Single Main Metric */}
        {dualBars && dualBars.length > 0 ? (
          <div className="space-y-3 mb-4">
            {dualBars.map((bar, idx) => {
              const barPct = Math.min(Math.max(bar.percentage || 0, 0), 100);
              return (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between items-baseline text-xs">
                    <span className="text-slate-600 dark:text-slate-400 font-medium">{bar.label}:</span>
                    <span className="font-mono text-slate-800 dark:text-slate-200 font-semibold">
                      {bar.used} / {bar.limit} <span className="text-[11px] font-normal text-slate-500">({barPct.toFixed(0)}%)</span>
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${bar.barColor || theme.bar}`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <>
            {/* Main Consumption Figures */}
            <div className="mb-4">
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{used}</span>
                <span className="text-sm text-slate-500 dark:text-slate-400">/ {limit} {unit}</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden mb-3">
              <div
                className={`h-full rounded-full transition-all duration-500 ${theme.bar}`}
                style={{ width: `${clampedPct}%` }}
              ></div>
            </div>
          </>
        )}
      </div>

      {/* Slot for custom details or sub-metrics */}
      {children && (
        <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 text-xs text-slate-600 dark:text-slate-400 space-y-1.5">
          {children}
        </div>
      )}
    </div>
  );
}

