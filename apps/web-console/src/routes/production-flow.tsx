import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { P145BatchValidation, P145DashboardRecord, P145ManualRequiredQueue, P145StuckRecovery } from "../lib/api-types";

const sampleTasks = [
  {
    run_id: "p14_5_w1_safe_window_preview",
    app_id: "p14_5_safe_window",
    role: "W1",
    capture_method: "windows_safe_window_capture",
    target_total: 30,
    worker_id: "worker_pc_game_w1"
  },
  {
    run_id: "p14_5_w2_web_content_preview",
    app_id: "p14_5_web_content",
    role: "W2",
    capture_method: "playwright_edge_content_only",
    target_total: 30,
    worker_id: "worker_pc_app_web_w2"
  },
  {
    run_id: "p14_5_w3_safe_ui_preview",
    app_id: "p14_5_android_safe_ui",
    role: "W3",
    capture_method: "adb_safe_ui_variation",
    target_total: 30,
    worker_id: "worker_android_w3"
  }
];

function guardLabel(value: boolean) {
  return value ? "blocked" : "off";
}

export function ProductionFlowRoute() {
  const [dashboard, setDashboard] = useState<P145DashboardRecord | null>(null);
  const [validation, setValidation] = useState<P145BatchValidation | null>(null);
  const [manualQueue, setManualQueue] = useState<P145ManualRequiredQueue | null>(null);
  const [recovery, setRecovery] = useState<P145StuckRecovery | null>(null);
  const [message, setMessage] = useState("");

  async function load() {
    const [dash, queue, validate, stuck] = await Promise.all([
      apiClient.getP145OperatorDashboard(),
      apiClient.getP145ManualRequired(),
      apiClient.validateP145BatchTasks({ tasks: sampleTasks, dry_run: true }),
      apiClient.recoverP145StuckTasks()
    ]);
    setDashboard(dash);
    setManualQueue(queue);
    setValidation(validate);
    setRecovery(stuck);
    setMessage(apiClient.isUsingMockFallback() ? "Master API unavailable, showing fallback preview data." : "Live P14.5 guard data loaded.");
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <PageHeader title="P14.5 生产流程" description="小规模任务导入、人工队列、上传确认、清理预览、磁盘检查和诊断包的受控操作面板。" />
      <div className="space-y-4">
        <Card
          title="安全边界"
          eyebrow="guards"
          action={
            <Button onClick={() => void load()}>
              <RefreshCw size={16} />
              刷新
            </Button>
          }
        >
          <p className="mb-3 text-sm text-slate-400">{message}</p>
          <div className="grid gap-3 md:grid-cols-5">
            {Object.entries(dashboard?.guards || {}).map(([key, value]) => (
              <div key={key} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="font-mono text-xs text-slate-500">{key}</p>
                <Badge className={value ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-slate-700 bg-slate-900 text-slate-300"}>{guardLabel(value)}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Batch dry-run" eyebrow="import preview">
            <DataTable columns={["run", "role", "method", "target", "status"]}>
              {(validation?.tasks || []).map((task, index) => (
                <tr key={String(task.run_id || index)}>
                  <td className="font-mono text-blue-300">{String(task.run_id || "-")}</td>
                  <td>{String(task.role || "-")}</td>
                  <td className="font-mono text-xs text-slate-500">{String(task.capture_method || "-")}</td>
                  <td>{String(task.target_total || "-")}</td>
                  <td>
                    <Badge className={task.valid ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-200"}>
                      {task.valid ? "valid" : "blocked"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </DataTable>
            <p className="mt-3 text-sm text-slate-500">
              dry_run={String(validation?.dry_run)} · production_scale_capture={String(validation?.production_scale_capture)}
            </p>
          </Card>

          <Card title="Manual required" eyebrow="operator queue">
            <DataTable columns={["run", "status", "worker", "reason"]}>
              {(manualQueue?.items || []).slice(0, 8).map((item) => (
                <tr key={item.run_id}>
                  <td className="font-mono text-blue-300">{item.run_id}</td>
                  <td>{item.status}</td>
                  <td className="font-mono text-xs text-slate-500">{item.worker_id || "-"}</td>
                  <td>{item.reason}</td>
                </tr>
              ))}
            </DataTable>
            {manualQueue?.count === 0 ? <p className="text-sm text-slate-400">暂无人工处理项。</p> : null}
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Disk status" eyebrow="M0 / workers">
            <DataTable columns={["node", "root", "status", "free"]}>
              {(dashboard?.disk.nodes || []).map((node) => (
                <tr key={node.role}>
                  <td>{node.role}</td>
                  <td className="font-mono text-xs text-slate-500">{node.root}</td>
                  <td>{node.status}</td>
                  <td>{node.free_gb ? `${node.free_gb} GB` : "-"}</td>
                </tr>
              ))}
            </DataTable>
          </Card>

          <Card title="Stuck recovery" eyebrow="dry-run only">
            <p className="text-sm text-slate-400">
              candidate_count={recovery?.candidate_count ?? 0} · mutated={String(recovery?.mutated ?? false)}
            </p>
            <DataTable columns={["run", "status", "action"]}>
              {(recovery?.candidates || []).slice(0, 8).map((item, index) => (
                <tr key={String(item.run_id || index)}>
                  <td className="font-mono text-blue-300">{String(item.run_id || "-")}</td>
                  <td>{String(item.status || "-")}</td>
                  <td>{String(item.recommended_action || "-")}</td>
                </tr>
              ))}
            </DataTable>
          </Card>
        </div>
      </div>
    </div>
  );
}
