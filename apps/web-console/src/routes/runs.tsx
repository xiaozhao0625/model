import { useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../lib/api-client";
import type { RunRecord, RunStatus } from "../lib/api-types";
import { mockApps, mockRuns } from "../lib/mock-data";
import { formatNumber } from "../lib/format";
import { actionLabels, bucketLabels, statusLabels } from "../lib/status";
import { PageHeader } from "../components/layout/page-header";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input, Select } from "../components/ui/input";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";

export function RunsRoute() {
  const [runs, setRuns] = useState<RunRecord[]>(mockRuns);
  const [statusFilter, setStatusFilter] = useState<"all" | RunStatus>("all");
  const [appFilter, setAppFilter] = useState("all");
  const [runId, setRunId] = useState("new_run");
  const [appId, setAppId] = useState(mockApps[0]?.app_id || "demo_app");

  const filtered = runs.filter((run) => (statusFilter === "all" || run.status === statusFilter) && (appFilter === "all" || run.app_id === appFilter));

  async function createRun() {
    const created = await apiClient.createRun({ run_id: runId, app_id: appId, target_min: 1000, target_max: 5000 });
    setRuns((current) => [created, ...current.filter((run) => run.run_id !== created.run_id)]);
  }

  async function startRun(id: string) {
    const updated = await apiClient.startRun(id);
    setRuns((current) => current.map((run) => (run.run_id === id ? updated : run)));
  }

  return (
    <div>
      <PageHeader title="任务控制中心" description="创建、筛选、启动和查看采集任务。P8 只调用 API 入口，不执行真实 Worker。" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="任务列表" eyebrow="运行队列">
          <div className="mb-4 grid gap-3 md:grid-cols-2">
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | RunStatus)}>
              <option value="all">全部状态</option>
              {[...new Set(runs.map((run) => run.status))].map((status) => (
                <option key={status} value={status}>
                  {statusLabels[status]}
                </option>
              ))}
            </Select>
            <Select value={appFilter} onChange={(event) => setAppFilter(event.target.value)}>
              <option value="all">全部应用</option>
              {mockApps.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.app_id}
                </option>
              ))}
            </Select>
          </div>
          <DataTable columns={["run_id", "app_id", "状态", "valid_total", "固定页 / 低频 / 高频 / 已拒绝", "补采轮次", "Worker", "操作"]}>
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
                    {bucketLabels.fixed}:{run.fixed_count} / {bucketLabels.low}:{run.low_count} / {bucketLabels.high}:{run.high_count} / {bucketLabels.rejected}:{run.rejected_count}
                </td>
                <td className="text-slate-400">{run.retry_round}</td>
                <td className="font-mono text-xs text-slate-500">{run.worker_id || "none"}</td>
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
        </Card>
        <Card title="新建任务" eyebrow="任务配置">
          <div className="grid gap-3">
            <Input value={runId} onChange={(event) => setRunId(event.target.value)} aria-label="任务 ID" />
            <Select value={appId} onChange={(event) => setAppId(event.target.value)} aria-label="应用 ID">
              {mockApps.map((app) => (
              <option key={app.app_id} value={app.app_id}>
                  {app.app_id}
                </option>
              ))}
            </Select>
            <Input readOnly value="target_min=1000" aria-label="最小目标" />
            <Input readOnly value="target_max=5000" aria-label="最大目标" />
            <Button variant="primary" onClick={() => void createRun()}>
              新建任务
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
