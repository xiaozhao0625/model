import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { apiClient } from "../lib/api-client";
import type { RunRecord } from "../lib/api-types";
import { mockMeta, mockRunLogs, mockRuns, mockSummary } from "../lib/mock-data";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";
import { RunActions } from "../components/runs/run-actions";
import { RunCountsPanel } from "../components/runs/run-counts-panel";
import { RunLogViewer } from "../components/runs/run-log-viewer";
import { RunStatusTimeline } from "../components/runs/run-status-timeline";
import { RunSummaryPanel } from "../components/runs/run-summary-panel";

export function RunDetailRoute() {
  const { runId = "run_capture_done" } = useParams();
  const initialRun = useMemo(() => mockRuns.find((run) => run.run_id === runId) || mockRuns[0], [runId]);
  const [run, setRun] = useState<RunRecord>(initialRun);
  const [message, setMessage] = useState("Actions call P7 API only. They do not execute local capture.");

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
    setMessage(`Action requested: ${action}`);
  }

  return (
    <div>
      <PageHeader title={`Run Detail: ${run.run_id}`} description="Inspect run lifecycle, bucket counts, summary.json, run.log, meta.jsonl, and state-gated action entry points." />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <Card title="Run Basics" eyebrow="state">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm text-slate-500">Status</p>
                <div className="mt-2">
                  <StatusPill status={run.status} />
                </div>
              </div>
              <div>
                <p className="text-sm text-slate-500">App</p>
                <p className="mt-2 font-mono text-sm text-slate-200">{run.app_id}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Worker</p>
                <p className="mt-2 font-mono text-sm text-slate-200">{run.worker_id || "unassigned"}</p>
              </div>
            </div>
          </Card>
          <Card title="Bucket Counts" eyebrow="completion gate">
            <RunCountsPanel run={run} />
          </Card>
          <Card title="summary.json" eyebrow="artifact">
            <RunSummaryPanel summary={{ ...mockSummary, ...run }} />
          </Card>
          <Card title="run.log" eyebrow="jsonl">
            <RunLogViewer logs={mockRunLogs} />
          </Card>
          <Card title="meta.jsonl" eyebrow="image metadata">
            <DataTable columns={["image_id", "bucket", "valid", "path", "content_hash / reason"]}>
              {mockMeta.map((item) => (
                <tr key={item.image_id}>
                  <td className="font-mono text-blue-300">{item.image_id}</td>
                  <td className="text-slate-300">{item.bucket}</td>
                  <td className={item.valid ? "text-emerald-300" : "text-red-300"}>{String(item.valid)}</td>
                  <td className="font-mono text-xs text-slate-500">{item.path}</td>
                  <td className="font-mono text-xs text-slate-500">{item.content_hash || item.reject_reason}</td>
                </tr>
              ))}
            </DataTable>
          </Card>
        </div>
        <div className="space-y-4">
          <Card title="Lifecycle" eyebrow="state flow">
            <RunStatusTimeline status={run.status} />
          </Card>
          <Card title="Actions" eyebrow="gated">
            <RunActions run={run} onAction={(action) => void handleAction(action)} />
            <p className="mt-3 text-xs text-slate-500">{message}</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
