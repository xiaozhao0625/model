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

export function RunDetailRoute() {
  const { runId = "run_capture_done" } = useParams();
  const initialRun = useMemo(() => mockRuns.find((run) => run.run_id === runId) || mockRuns[0], [runId]);
  const [run, setRun] = useState<RunRecord>(initialRun);
  const [message, setMessage] = useState("操作只调用 Master API，不直接触碰 Worker 文件。");

  useEffect(() => {
    void apiClient.getRun(runId).then(setRun);
  }, [runId]);

  async function handleAction(action: string) {
    if (action === "start") {
      setRun(await apiClient.startRun(run.run_id));
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
    setMessage(`已请求操作：${action}`);
  }

  return (
    <div>
      <PageHeader title={`任务详情：${run.run_id}`} description="查看任务生命周期、分桶数量、summary.json、run.log、meta.jsonl 和受控产物操作。" />
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
                <p className="mt-2 font-mono text-sm text-slate-200">{run.worker_id || "未分配"}</p>
              </div>
            </div>
          </Card>
          <Card title="分桶数量" eyebrow="完成门禁">
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
            <DataTable columns={["图片 ID", "分桶", "有效", "路径", "内容哈希 / 原因"]}>
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
            <p className="mt-3 text-xs text-slate-500">{message}</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
