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

  useEffect(() => {
    let active = true;

    Promise.all([apiClient.listRuns(), apiClient.listApps()])
      .then(([runRecords, appRecords]) => {
        if (!active) {
          return;
        }
        setRuns(runRecords);
        setApps(appRecords);
        setAppId((current) => current || appRecords[0]?.app_id || "");
        setUsingFallback(apiClient.isUsingMockFallback());
        const fallbackError = apiClient.getFallbackError();
        setFallbackDetail(
          fallbackError
            ? `${fallbackError.api_base_url}${fallbackError.failed_endpoint}: ${fallbackError.status || "network"} ${fallbackError.error}`
            : ""
        );
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
    setRuns((current) => [created, ...current.filter((run) => run.run_id !== created.run_id)]);
  }

  async function startRun(id: string) {
    const updated = await apiClient.startRun(id);
    setRuns((current) => current.map((run) => (run.run_id === id ? updated : run)));
  }

  return (
    <div>
      <PageHeader title="Run Control Center" description="Create, filter, start, and inspect capture runs from the live Master API." />
      {usingFallback ? (
        <div className="mb-4 rounded-[10px] border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          Run data is using local demo fallback because the live Master API request failed.
          {fallbackDetail ? <span className="mt-1 block font-mono text-xs text-amber-200">{fallbackDetail}</span> : null}
        </div>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="Run List" eyebrow="live queue">
          <div className="mb-4 grid gap-3 md:grid-cols-2">
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | RunStatus)}>
              <option value="all">All statuses</option>
              {[...new Set(runs.map((run) => run.status))].map((status) => (
                <option key={status} value={status}>
                  {statusLabels[status] || status}
                </option>
              ))}
            </Select>
            <Select value={appFilter} onChange={(event) => setAppFilter(event.target.value)}>
              <option value="all">All apps</option>
              {appOptions.map((app) => (
                <option key={app} value={app}>
                  {app}
                </option>
              ))}
            </Select>
          </div>
          {loading ? (
            <p className="text-sm text-slate-400">Loading runs from {apiClient.getBaseUrl()}...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-slate-400">No runs reported by the Master API.</p>
          ) : (
            <DataTable columns={["run_id", "app_id", "status", "valid_total", "fixed / low / high / rejected", "retry", "worker", "actions"]}>
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
          )}
        </Card>
        <Card title="Create Run" eyebrow="live API">
          <div className="grid gap-3">
            <Input value={runId} onChange={(event) => setRunId(event.target.value)} aria-label="Run ID" />
            <Select value={appId} onChange={(event) => setAppId(event.target.value)} aria-label="App ID">
              {appOptions.map((app) => (
                <option key={app} value={app}>
                  {app}
                </option>
              ))}
            </Select>
            <Input readOnly value="target_min=1000" aria-label="Minimum target" />
            <Input readOnly value="target_max=5000" aria-label="Maximum target" />
            <Button variant="primary" disabled={!appId || !runId} onClick={() => void createRun()}>
              Create run
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
