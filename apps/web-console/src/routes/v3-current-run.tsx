import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3RunRecord, V3Summary } from "../lib/api-types";
import { labelStatus } from "../lib/labels";

export function V3CurrentRunRoute() {
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [summaries, setSummaries] = useState<Record<string, V3Summary>>({});

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    const nextRuns = await apiClient.listV3Runs();
    setRuns(nextRuns);
    const entries = await Promise.all(nextRuns.slice(0, 10).map(async (run) => [run.run_id, await apiClient.getV3Summary(run.run_id)] as const));
    setSummaries(Object.fromEntries(entries));
  }

  return (
    <div>
      <PageHeader title="当前运行" description="查看最近任务的 processed、accepted、rejected、failed、quarantined 和动作数量。" />
      <div className="grid gap-3">
        {runs.length === 0 ? <Card title="暂无任务"><p className="text-sm text-slate-500">还没有 V3 run。</p></Card> : null}
        {runs.slice(0, 10).map((run) => {
          const summary = summaries[run.run_id];
          return (
            <Card key={run.run_id} title={run.config.app_name} eyebrow={run.run_id}>
              <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-8">
                <Metric label="状态" value={labelStatus(run.status)} />
                <Metric label="app_type" value={run.config.app_type} />
                <Metric label="processed" value={String(summary?.processed ?? 0)} />
                <Metric label="accepted" value={String(summary?.accepted ?? run.counts.accepted ?? 0)} />
                <Metric label="rejected" value={String(summary?.rejected ?? run.counts.rejected ?? 0)} />
                <Metric label="failed" value={String(summary?.failed ?? 0)} />
                <Metric label="quarantined" value={String(summary?.quarantined ?? 0)} />
                <Metric label="action_count" value={String(run.counts.actions ?? 0)} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" to={`/v3/runs/${run.run_id}/gallery`}>
                  查看结果图库
                </Link>
                <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${run.run_id}/actions`}>
                  查看运行详情 / 审计
                </Link>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 break-all text-base font-semibold text-slate-100">{value}</p>
    </div>
  );
}
