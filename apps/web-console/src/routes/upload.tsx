import { useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { CleanupDangerZone } from "../components/upload/cleanup-danger-zone";
import { UploadFlowPanel } from "../components/upload/upload-flow-panel";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { RunRecord } from "../lib/api-types";
import { mockRuns } from "../lib/mock-data";
import { actionLabels } from "../lib/status";

export function UploadRoute() {
  const [runs, setRuns] = useState<RunRecord[]>(mockRuns.filter((run) => ["capture_completed", "upload_pending", "uploaded_confirmed", "local_deleted"].includes(run.status)));
  const [message, setMessage] = useState("本页只生成上传清单和记录操作状态，不直接上传外部网盘。");

  async function update(run: RunRecord, action: "manifest" | "confirm" | "cleanup" | "finalize") {
    const result =
      action === "manifest"
        ? await apiClient.generateUploadManifest(run.run_id)
        : action === "confirm"
          ? await apiClient.confirmUpload(run.run_id)
          : action === "cleanup"
            ? await apiClient.cleanupLocal(run.run_id)
            : await apiClient.finalizeRun(run.run_id);
    setRuns((current) => current.map((item) => (item.run_id === run.run_id ? { ...item, status: result.status } : item)));
    setMessage(`已请求 ${action}：${run.run_id}`);
  }

  const focused = runs[0] || mockRuns[1];

  return (
    <div>
      <PageHeader title="上传与清理" description="按 run 维度执行上传清单、确认上传、本地清理和最终完成；删除本地文件前必须人工确认。" />
      <div className="space-y-4">
        <Card title="P2 状态流规则" eyebrow="状态门禁">
          <UploadFlowPanel status={focused.status} />
          <p className="mt-4 text-sm text-slate-500">{message}</p>
        </Card>
        <Card title="上传队列" eyebrow="任务">
          <DataTable columns={["任务", "状态", "上传清单", "上传记录", "清理记录", "操作"]}>
            {runs.map((run) => (
              <tr key={run.run_id}>
                <td className="font-mono text-blue-300">{run.run_id}</td>
                <td>
                  <StatusPill status={run.status} />
                </td>
                <td className="text-slate-400">{["upload_pending", "uploaded_confirmed", "local_deleted"].includes(run.status) ? "已生成" : "待生成"}</td>
                <td className="text-slate-400">{["uploaded_confirmed", "local_deleted"].includes(run.status) ? "已确认" : "未确认"}</td>
                <td className="text-slate-400">{run.status === "local_deleted" ? "已清理" : "未清理"}</td>
                <td>
                  <div className="flex flex-wrap gap-2">
                    <Button disabled={run.status !== "capture_completed"} onClick={() => void update(run, "manifest")}>
                      {actionLabels.upload_manifest}
                    </Button>
                    <Button disabled={run.status !== "upload_pending"} onClick={() => void update(run, "confirm")}>
                      {actionLabels.confirm_upload}
                    </Button>
                    <Button disabled={run.status !== "uploaded_confirmed"} onClick={() => void update(run, "cleanup")}>
                      {actionLabels.cleanup}
                    </Button>
                    <Button disabled={run.status !== "local_deleted"} onClick={() => void update(run, "finalize")}>
                      {actionLabels.finalize}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </DataTable>
        </Card>
        <CleanupDangerZone disabled={focused.status !== "uploaded_confirmed"} onCleanup={() => void update(focused, "cleanup")} />
      </div>
    </div>
  );
}
