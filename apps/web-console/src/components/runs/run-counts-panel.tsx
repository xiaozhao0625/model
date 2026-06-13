import type { RunRecord } from "../../lib/api-types";
import { formatNumber, formatPercent } from "../../lib/format";

export function RunCountsPanel({ run }: { run: RunRecord }) {
  const target = run.target_min || 1000;
  const progress = Math.min(100, Math.round((run.valid_total / target) * 100));
  return (
    <div>
      <div className="mb-3 flex items-end justify-between">
        <div>
          <p className="text-sm text-slate-400">valid_total progress</p>
          <p className="mt-1 text-2xl font-semibold text-slate-50">{formatNumber(run.valid_total)}</p>
        </div>
        <p className="font-mono text-sm text-slate-500">{progress}% of target</p>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className="h-full rounded-full bg-blue-400" style={{ width: `${progress}%` }} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        {[
          ["fixed", run.fixed_count],
          ["low", run.low_count],
          ["high", run.high_count],
          ["rejected", run.rejected_count]
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
            <p className="capitalize text-slate-400">{label}</p>
            <p className="mt-1 font-mono text-slate-100">{formatNumber(Number(value))}</p>
            <p className="mt-1 text-xs text-slate-600">{formatPercent(Number(value), Math.max(run.valid_total, 1))}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
