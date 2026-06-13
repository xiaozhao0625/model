import { useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../lib/api-client";
import type { RunRecord, RunStatus } from "../lib/api-types";
import { mockApps, mockRuns } from "../lib/mock-data";
import { formatNumber } from "../lib/format";
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
      <PageHeader title="Run Control" description="Create, filter, start, and inspect capture runs. Worker execution remains outside this UI stage." />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="Runs" eyebrow="list">
          <div className="mb-4 grid gap-3 md:grid-cols-2">
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | RunStatus)}>
              <option value="all">all statuses</option>
              {[...new Set(runs.map((run) => run.status))].map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </Select>
            <Select value={appFilter} onChange={(event) => setAppFilter(event.target.value)}>
              <option value="all">all apps</option>
              {mockApps.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.app_id}
                </option>
              ))}
            </Select>
          </div>
          <DataTable columns={["run_id", "app_id", "status", "valid_total", "fixed / low / high / rejected", "retry", "worker", "action"]}>
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
                  {run.fixed_count} / {run.low_count} / {run.high_count} / {run.rejected_count}
                </td>
                <td className="text-slate-400">{run.retry_round}</td>
                <td className="font-mono text-xs text-slate-500">{run.worker_id || "none"}</td>
                <td>
                  <Button disabled={run.status !== "pending"} onClick={() => void startRun(run.run_id)}>
                    Start Run
                  </Button>
                </td>
              </tr>
            ))}
          </DataTable>
        </Card>
        <Card title="Create Run" eyebrow="task">
          <div className="grid gap-3">
            <Input value={runId} onChange={(event) => setRunId(event.target.value)} aria-label="run id" />
            <Select value={appId} onChange={(event) => setAppId(event.target.value)} aria-label="app id">
              {mockApps.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.app_id}
                </option>
              ))}
            </Select>
            <Input readOnly value="target_min=1000" aria-label="target min" />
            <Input readOnly value="target_max=5000" aria-label="target max" />
            <Button variant="primary" onClick={() => void createRun()}>
              Create Run
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
