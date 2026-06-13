import { mockRuns } from "../../lib/mock-data";
import { formatNumber } from "../../lib/format";
import { bucketLabels } from "../../lib/status";

export function CaptureHealth() {
  const totals = mockRuns.reduce(
    (acc, run) => ({
      fixed: acc.fixed + run.fixed_count,
      low: acc.low + run.low_count,
      high: acc.high + run.high_count,
      rejected: acc.rejected + run.rejected_count
    }),
    { fixed: 0, low: 0, high: 0, rejected: 0 }
  );
  const max = Math.max(totals.fixed, totals.low, totals.high, totals.rejected, 1);

  return (
    <div className="space-y-4">
      {Object.entries(totals).map(([bucket, count]) => (
        <div key={bucket}>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-slate-300">{bucketLabels[bucket] || bucket}</span>
            <span className="font-mono text-slate-500">{formatNumber(count)}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full ${
                bucket === "high" ? "bg-blue-400" : bucket === "low" ? "bg-emerald-400" : bucket === "rejected" ? "bg-red-400" : "bg-slate-400"
              }`}
              style={{ width: `${Math.max(3, Math.round((count / max) * 100))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
