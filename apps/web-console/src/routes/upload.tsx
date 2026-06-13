import { useState } from "react";
import { apiClient } from "../lib/api-client";
import { mockRuns } from "../lib/mock-data";
import type { RunRecord } from "../lib/api-types";
import { PageHeader } from "../components/layout/page-header";
import { CleanupDangerZone } from "../components/upload/cleanup-danger-zone";
import { UploadFlowPanel } from "../components/upload/upload-flow-panel";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { StatusPill } from "../components/ui/status-pill";
import { DataTable } from "../components/ui/table";

export function UploadRoute() {
  const [runs, setRuns] = useState<RunRecord[]>(mockRuns.filter((run) => ["capture_completed", "upload_pending", "uploaded_confirmed", "local_deleted"].includes(run.status)));
  const [message, setMessage] = useState("No real Baidu Netdisk API is called in P8.");

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
    setMessage(`${action} requested for ${run.run_id}`);
  }

  const focused = runs[0] || mockRuns[1];

  return (
    <div>
      <PageHeader title="Upload & Cleanup" description="Run-scoped upload and cleanup operations. Manual Baidu Netdisk confirmation remains mandatory before deletion." />
      <div className="space-y-4">
        <Card title="P2 Lifecycle Rules" eyebrow="canonical">
          <UploadFlowPanel status={focused.status} />
          <p className="mt-4 text-sm text-slate-500">{message}</p>
        </Card>
        <Card title="Upload Queue" eyebrow="runs">
          <DataTable columns={["run", "status", "manifest", "upload record", "cleanup record", "actions"]}>
            {runs.map((run) => (
              <tr key={run.run_id}>
                <td className="font-mono text-blue-300">{run.run_id}</td>
                <td>
                  <StatusPill status={run.status} />
                </td>
                <td className="text-slate-400">{["upload_pending", "uploaded_confirmed", "local_deleted"].includes(run.status) ? "ready" : "pending"}</td>
                <td className="text-slate-400">{["uploaded_confirmed", "local_deleted"].includes(run.status) ? "confirmed" : "not yet"}</td>
                <td className="text-slate-400">{run.status === "local_deleted" ? "ready" : "not yet"}</td>
                <td>
                  <div className="flex flex-wrap gap-2">
                    <Button disabled={run.status !== "capture_completed"} onClick={() => void update(run, "manifest")}>
                      Manifest
                    </Button>
                    <Button disabled={run.status !== "upload_pending"} onClick={() => void update(run, "confirm")}>
                      Confirm Uploaded
                    </Button>
                    <Button disabled={run.status !== "uploaded_confirmed"} onClick={() => void update(run, "cleanup")}>
                      Cleanup
                    </Button>
                    <Button disabled={run.status !== "local_deleted"} onClick={() => void update(run, "finalize")}>
                      Finalize
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
