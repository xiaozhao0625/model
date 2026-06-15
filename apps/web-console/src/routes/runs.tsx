import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input, Select } from "../components/ui/input";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { AppRecord, RunListResponse, RunRecord, RunStatus } from "../lib/api-types";
import { formatNumber } from "../lib/format";
import { actionLabels, bucketLabels, statusLabels } from "../lib/status";

const workerOptions = [
  ["all", "全部机器"],
  ["worker_pc_game_w1", "W1 PC Game"],
  ["worker_pc_app_web_w2", "W2 Web / PC App"],
  ["worker_android_w3", "W3 Android"],
  ["unassigned", "未分配"]
];

const batchOptions = [
  ["all", "全部批次"],
  ["latest", "最近任务"],
  ["p14_4_batch1", "P14.4 Batch1"],
  ["p14_4_batch2", "P14.4 Batch2"],
  ["p14_4_batch3", "P14.4 Batch3"],
  ["p14_3", "P14.3"]
];

const sortOptions = [
  ["created_at_desc", "最新优先"],
  ["created_at_asc", "最旧优先"],
  ["status_priority", "失败优先"],
  ["valid_total_desc", "有效图最多"],
  ["worker_id_asc", "Worker 排序"]
];

const statusOptions: Array<[string, string]> = [
  ["all", "全部状态"],
  ["capture_completed", "采集完成"],
  ["running", "运行中"],
  ["failed_low_yield", "低产失败"],
  ["skipped_risk", "风险跳过"],
  ["waiting_manual", "等待人工"],
  ["pending", "待处理"]
];

function workerLabel(run: RunRecord) {
  return run.executed_by || run.assigned_worker_id || run.worker_id || "未分配";
}

function queryValue(params: URLSearchParams, key: string, fallback: string) {
  return params.get(key) || fallback;
}

export function RunsRoute() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [result, setResult] = useState<RunListResponse | null>(null);
  const [apps, setApps] = useState<AppRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [fallbackDetail, setFallbackDetail] = useState("");
  const [runId, setRunId] = useState("new_run");
  const [appId, setAppId] = useState("");

  const filters = {
    status: queryValue(searchParams, "status", "all"),
    worker_id: queryValue(searchParams, "worker_id", "all"),
    app_id: queryValue(searchParams, "app_id", "all"),
    batch: queryValue(searchParams, "batch", "all"),
    q: queryValue(searchParams, "q", ""),
    created_from: queryValue(searchParams, "created_from", ""),
    created_to: queryValue(searchParams, "created_to", ""),
    sort: queryValue(searchParams, "sort", "created_at_desc"),
    limit: queryValue(searchParams, "limit", "50"),
    offset: queryValue(searchParams, "offset", "0")
  };

  async function loadData() {
    setLoading(true);
    const [runResult, appRecords] = await Promise.all([apiClient.listRuns(filters), apiClient.listApps()]);
    setResult(runResult);
    setRuns(runResult.items);
    setApps(appRecords);
    setAppId((current) => current || appRecords[0]?.app_id || "");
    setUsingFallback(apiClient.isUsingMockFallback());
    const fallbackError = apiClient.getFallbackError();
    setFallbackDetail(
      fallbackError ? `${fallbackError.api_base_url}${fallbackError.failed_endpoint}: ${fallbackError.status || "network"} ${fallbackError.error}` : ""
    );
    setLoading(false);
  }

  useEffect(() => {
    let active = true;
    loadData().catch((err) => {
      if (active) {
        setFallbackDetail(err instanceof Error ? err.message : String(err));
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, [searchParams.toString()]);

  const appOptions = useMemo(() => {
    const values = new Set(apps.map((app) => app.app_id));
    for (const run of runs) {
      values.add(run.app_id);
    }
    return [...values].sort();
  }, [apps, runs]);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all" || (key === "sort" && value === "created_at_desc") || (key === "limit" && value === "50")) {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    if (key !== "offset") {
      next.delete("offset");
    }
    setSearchParams(next);
  }

  async function createRun() {
    if (!appId || !runId) {
      return;
    }
    await apiClient.createRun({ run_id: runId, app_id: appId, target_min: 1000, target_max: 5000 });
    setFilter("sort", "created_at_desc");
    await loadData();
  }

  async function startRun(id: string) {
    await apiClient.startRun(id);
    await loadData();
  }

  const total = result?.total ?? runs.length;
  const limit = Number(filters.limit);
  const offset = Number(filters.offset);
  const canPrev = offset > 0;
  const canNext = offset + limit < total;

  return (
    <div>
      <PageHeader title="采集任务" description="按时间、Worker、状态和批次快速定位 run；默认最新任务在最上方。" />
      {usingFallback ? (
        <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          实时 Master API 请求失败，当前显示本地演示兜底数据。
          {fallbackDetail ? <span className="mt-1 block font-mono text-xs text-amber-200">{fallbackDetail}</span> : null}
        </div>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="任务列表" eyebrow="查询 / 筛选 / 排序">
          <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Select value={filters.status} onChange={(event) => setFilter("status", event.target.value)} aria-label="状态筛选">
              {statusOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select value={filters.worker_id} onChange={(event) => setFilter("worker_id", event.target.value)} aria-label="Worker 筛选">
              {workerOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select value={filters.batch} onChange={(event) => setFilter("batch", event.target.value)} aria-label="批次筛选">
              {batchOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select value={filters.sort} onChange={(event) => setFilter("sort", event.target.value)} aria-label="排序">
              {sortOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select value={filters.app_id} onChange={(event) => setFilter("app_id", event.target.value)} aria-label="应用筛选">
              <option value="all">全部应用</option>
              {appOptions.map((app) => (
                <option key={app} value={app}>
                  {app}
                </option>
              ))}
            </Select>
            <Input value={filters.created_from} onChange={(event) => setFilter("created_from", event.target.value)} placeholder="开始时间 YYYY-MM-DD" aria-label="开始时间" />
            <Input value={filters.created_to} onChange={(event) => setFilter("created_to", event.target.value)} placeholder="结束时间 YYYY-MM-DD" aria-label="结束时间" />
            <div className="flex gap-2">
              <Input value={filters.q} onChange={(event) => setFilter("q", event.target.value)} placeholder="搜索 run / app / worker" aria-label="搜索" />
              <button className="inline-flex min-h-10 w-10 items-center justify-center rounded-lg border border-slate-700 bg-slate-950 text-slate-300" title="搜索">
                <Search size={16} />
              </button>
            </div>
          </div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
            <span>
              共 {total} 条，当前 {offset + 1}-{Math.min(offset + limit, total)}
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={filters.limit} onChange={(event) => setFilter("limit", event.target.value)} aria-label="每页数量">
                <option value="50">每页 50</option>
                <option value="100">每页 100</option>
                <option value="200">每页 200</option>
              </Select>
              <Button disabled={!canPrev} onClick={() => setFilter("offset", String(Math.max(0, offset - limit)))}>
                上一页
              </Button>
              <Button disabled={!canNext} onClick={() => setFilter("offset", String(offset + limit))}>
                下一页
              </Button>
            </div>
          </div>
          {loading ? (
            <p className="text-sm text-slate-400">正在从 {apiClient.getBaseUrl()} 加载任务...</p>
          ) : runs.length === 0 ? (
            <p className="text-sm text-slate-400">没有符合条件的任务。</p>
          ) : (
            <DataTable columns={["任务 ID", "应用 ID", "状态", "有效数", "固定 / 低频 / 高频 / 拒绝", "批次", "Worker", "创建时间", "操作"]}>
              {runs.map((run) => (
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
                  <td className="font-mono text-xs text-slate-500">{run.batch || "-"}</td>
                  <td className="font-mono text-xs text-slate-500">{workerLabel(run)}</td>
                  <td className="font-mono text-xs text-slate-500">{run.created_at || "-"}</td>
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
