import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input, Select } from "../components/ui/input";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { AppRecord, RunRecord, RunStatus } from "../lib/api-types";
import { formatNumber } from "../lib/format";
import { actionLabels, bucketLabels, statusLabels } from "../lib/status";

function workerLabel(run: RunRecord) {
  return run.executed_by || run.assigned_worker_id || run.worker_id || "未分配";
}

export function RunsRoute() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [apps, setApps] = useState<AppRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [fallbackDetail, setFallbackDetail] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | RunStatus>("all");
  const [appFilter, setAppFilter] = useState("all");
  const [runId, setRunId] = useState("new_run");
  const [appId, setAppId] = useState("");

  async function loadData() {
    const [runRecords, appRecords] = await Promise.all([apiClient.listRuns(), apiClient.listApps()]);
    setRuns(runRecords);
    setApps(appRecords);
    setAppId((current) => current || appRecords[0]?.app_id || "");
    setUsingFallback(apiClient.isUsingMockFallback());
    const fallbackError = apiClient.getFallbackError();
    setFallbackDetail(
      fallbackError ? `${fallbackError.api_base_url}${fallbackError.failed_endpoint}: ${fallbackError.status || "network"} ${fallbackError.error}` : ""
    );
  }

  useEffect(() => {
    let active = true;
    loadData()
      .catch((err) => {
        if (active) {
          setFallbackDetail(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const appOptions = useMemo(() => {
    const values = new Set(apps.map((app) => app.app_id));
    for (const run of runs) {
      values.add(run.app_id);
    }
    return [...values].sort();
  }, [apps, runs]);

  const filtered = runs.filter((run) => (statusFilter === "all" || run.status === statusFilter) && (appFilter === "all" || run.app_id === appFilter));

  async function createRun() {
    if (!appId || !runId) {
      return;
    }
    const created = await apiClient.createRun({ run_id: runId, app_id: appId, target_min: 1000, target_max: 5000 });
    await loadData();
    setRuns((current) => [created, ...current.filter((run) => run.run_id !== created.run_id)]);
  }

  async function startRun(id: string) {
    await apiClient.startRun(id);
    await loadData();
  }

  return (
    <div>
      <PageHeader title="采集任务" description="从实时 Master API 创建、筛选、启动和查看采集任务。" />
      {usingFallback ? (
        <div className="mb-4 rounded-[10px] border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          实时 Master API 请求失败，当前显示本地演示兜底数据。
          {fallbackDetail ? <span className="mt-1 block font-mono text-xs text-amber-200">{fallbackDetail}</span> : null}
        </div>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="任务列表" eyebrow="实时队列">
          <div className="mb-4 grid gap-3 md:grid-cols-2">
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | RunStatus)}>
              <option value="all">全部状态</option>
              {[...new Set(runs.map((run) => run.status))].map((status) => (
                <option key={status} value={status}>
                  {statusLabels[status] || status}
                </option>
              ))}
            </Select>
            <Select value={appFilter} onChange={(event) => setAppFilter(event.target.value)}>
              <option value="all">全部应用</option>
              {appOptions.map((app) => (
                <option key={app} value={app}>
                  {app}
                </option>
              ))}
            </Select>
          </div>
          {loading ? (
            <p className="text-sm text-slate-400">正在从 {apiClient.getBaseUrl()} 加载任务...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-slate-400">Master API 暂无任务。</p>
          ) : (
            <DataTable columns={["任务 ID", "应用 ID", "状态", "有效数", "修复 / 低质 / 高质 / 拒绝", "重试", "Worker", "操作"]}>
              {filtered.map((run) => (
                <tr key={run.run_id}>
                  <td>
                    <Link to={`/runs/${run.run_id}`} className="font-mono text-blue-300 hover:text-blue-200">
                      {run.run_id}
                    </Link>
                  </td>
                  <td className="text-slate-300">{run.app_id}</td>
                  <td>
                    <StatusPill status={run.status} />
                  </td>
                  <td className="font-mono text-slate-300">{formatNumber(run.valid_total)}</td>
                  <td className="font-mono text-xs text-slate-500">
                    {bucketLabels.fixed}:{run.fixed_count} / {bucketLabels.low}:{run.low_count} / {bucketLabels.high}:{run.high_count} / {bucketLabels.rejected}:
                    {run.rejected_count}
                  </td>
                  <td className="text-slate-400">{run.retry_round}</td>
                  <td className="font-mono text-xs text-slate-500">{workerLabel(run)}</td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      <Button disabled={run.status !== "pending"} onClick={() => void startRun(run.run_id)}>
                        {actionLabels.start}
                      </Button>
                      <Link className="inline-flex min-h-9 items-center rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-medium text-slate-100 hover:border-slate-500" to={`/runs/${run.run_id}`}>
                        {actionLabels.view_detail}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </DataTable>
          )}
        </Card>
        <Card title="创建任务" eyebrow="实时 API">
          <div className="grid gap-3">
            <Input value={runId} onChange={(event) => setRunId(event.target.value)} aria-label="任务 ID" />
            <Select value={appId} onChange={(event) => setAppId(event.target.value)} aria-label="应用 ID">
              {appOptions.map((app) => (
                <option key={app} value={app}>
                  {app}
                </option>
              ))}
            </Select>
            <Input readOnly value="target_min=1000" aria-label="最小目标数" />
            <Input readOnly value="target_max=5000" aria-label="最大目标数" />
            <Button variant="primary" disabled={!appId || !runId} onClick={() => void createRun()}>
              创建任务
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
