import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { RunActions } from "../components/runs/run-actions";
import { RunArtifactInspector } from "../components/runs/run-artifact-inspector";
import { RunCountsPanel } from "../components/runs/run-counts-panel";
import { RunLogViewer } from "../components/runs/run-log-viewer";
import { RunStatusTimeline } from "../components/runs/run-status-timeline";
import { RunSummaryPanel } from "../components/runs/run-summary-panel";
import { Card } from "../components/ui/card";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { RunRecord } from "../lib/api-types";
import { mockMeta, mockRunLogs, mockRuns, mockSummary } from "../lib/mock-data";
import { bucketLabels } from "../lib/status";

function workerLabel(run: RunRecord) {
  return run.executed_by || run.assigned_worker_id || run.worker_id || "未分配";
}

export function RunDetailRoute() {
  const { runId = "run_capture_done" } = useParams();
  const initialRun = useMemo(() => mockRuns.find((item) => item.run_id === runId) || mockRuns[0], [runId]);
  const [run, setRun] = useState<RunRecord>(initialRun);
  const [message, setMessage] = useState("操作只调用 Master API，不直接触碰 Worker 文件。");
  const [error, setError] = useState<string | null>(null);

  async function refreshRun() {
    const record = await apiClient.getRun(runId);
    setRun(record);
    return record;
  }

  useEffect(() => {
    void refreshRun().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [runId]);

  async function handleAction(action: string) {
    setError(null);
    try {
      if (action === "start") {
        setRun(await apiClient.startRun(run.run_id));
      } else if (action === "mark_failed") {
        setRun(await apiClient.markRunFailedLowYield(run.run_id));
      } else if (action === "upload_manifest") {
        const result = await apiClient.generateUploadManifest(run.run_id);
        setRun((current) => ({ ...current, status: result.status }));
      } else if (action === "confirm_upload") {
        const result = await apiClient.confirmUpload(run.run_id);
        setRun((current) => ({ ...current, status: result.status }));
      } else if (action === "cleanup") {
        const result = await apiClient.cleanupLocal(run.run_id);
        setRun((current) => ({ ...current, status: result.status }));
      } else if (action === "finalize") {
        const result = await apiClient.finalizeRun(run.run_id);
        setRun((current) => ({ ...current, status: result.status }));
      }
      const latest = await refreshRun();
      setMessage(`已请求操作：${action}，当前状态：${latest.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setMessage(`操作失败：${action}`);
    }
  }

  return (
    <div>
      <PageHeader title={`任务详情：${run.run_id}`} description="查看任务生命周期、分档数量、summary.json、run.log、meta.jsonl 和受控产物操作。" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <Card title="任务基础信息" eyebrow="状态">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm text-slate-500">状态</p>
                <div className="mt-2">
                  <StatusPill status={run.status} />
                </div>
              </div>
              <div>
                <p className="text-sm text-slate-500">应用</p>
                <p className="mt-2 font-mono text-sm text-slate-200">{run.app_id}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Worker</p>
                <p className="mt-2 font-mono text-sm text-slate-200">{workerLabel(run)}</p>
              </div>
            </div>
          </Card>
          <Card title="分档数量" eyebrow="完成门槛">
            <RunCountsPanel run={run} />
          </Card>
          <RunArtifactInspector runId={runId} />
          <Card title="summary.json" eyebrow="产物">
            <RunSummaryPanel summary={{ ...mockSummary, ...run }} />
          </Card>
          <Card title="run.log" eyebrow="jsonl">
            <RunLogViewer logs={mockRunLogs} />
          </Card>
          <Card title="meta.jsonl" eyebrow="截图元数据">
            <DataTable columns={["图片 ID", "分档", "有效", "路径", "内容哈希 / 原因"]}>
              {mockMeta.map((item) => (
                <tr key={item.image_id}>
                  <td className="font-mono text-blue-300">{item.image_id}</td>
                  <td className="text-slate-300">{bucketLabels[item.bucket] || item.bucket}</td>
                  <td className={item.valid ? "text-emerald-300" : "text-red-300"}>{String(item.valid)}</td>
                  <td className="font-mono text-xs text-slate-500">{item.path}</td>
                  <td className="font-mono text-xs text-slate-500">{item.content_hash || item.reject_reason}</td>
                </tr>
              ))}
            </DataTable>
          </Card>
        </div>
        <div className="space-y-4">
          <Card title="生命周期" eyebrow="状态流">
            <RunStatusTimeline status={run.status} />
          </Card>
          <Card title="操作" eyebrow="受控 API">
            <RunActions run={run} onAction={(action) => void handleAction(action)} />
            <p className={error ? "mt-3 text-xs text-red-300" : "mt-3 text-xs text-slate-500"}>{error || message}</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
