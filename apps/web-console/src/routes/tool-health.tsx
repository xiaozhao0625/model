import { Activity, ServerCog } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { apiClient } from "../lib/api-client";
import type { ToolHealthRecord } from "../lib/api-types";
import { labelStatus } from "../lib/labels";
import { mockToolHealth } from "../lib/mock-data";

export function ToolHealthRoute() {
  const [health, setHealth] = useState<ToolHealthRecord>(mockToolHealth);

  useEffect(() => {
    void apiClient.getToolHealth().then(setHealth);
  }, []);

  return (
    <div>
      <PageHeader title="工具健康" description="展示本机工具、ADB、OCR fallback 与输入能力状态；不可用工具显示为不可用/跳过，不阻塞控制台显示。" />
      <div className="grid gap-4 lg:grid-cols-3">
        <HealthCard title="机器就绪（machine_ready）" status={health.machine_ready} />
        <HealthCard title="主服务就绪（master_ready）" status={health.master_ready} />
        <HealthCard title="Worker 就绪（worker_ready）" status={health.worker_ready} />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card title="工具状态" eyebrow="worker readiness">
          <DataTable columns={["工具", "状态"]}>
            {Object.entries(health.tools).map(([name, status]) => (
              <tr key={name}>
                <td className="font-mono text-slate-300">{name}</td>
                <td>
                  <Badge className={statusClass(status)}>{labelStatus(status)}</Badge>
                </td>
              </tr>
            ))}
          </DataTable>
        </Card>
        <Card title="Android 运行时" eyebrow="emulator / adb">
          <div className="grid gap-3">
            <Field label="ADB 可用（adb_available）" value={health.android.adb_available ? "true" : "false"} />
            <Field label="设备列表（devices）" value={health.android.devices.length ? health.android.devices.join(", ") : "[]"} />
            <Field label="选中设备（selected_device）" value={health.android.selected_device || "-"} />
            <Field label="截图状态（screencap_status）" value={health.android.screencap_status} />
            <Field label="UI dump 状态（ui_dump_status）" value={health.android.ui_dump_status} />
            <Field label="OCR fallback 状态（ocr_fallback_status）" value={health.android.ocr_fallback_status} />
            <Field label="输入状态（input_status）" value={health.android.input_status} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function HealthCard({ title, status }: { title: string; status: string }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-300">
          {title.includes("master_ready") ? <ServerCog size={19} /> : <Activity size={19} />}
        </div>
        <div>
          <p className="text-xs text-slate-500">{title}</p>
          <Badge className={statusClass(status)}>{labelStatus(status)}</Badge>
        </div>
      </div>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm text-slate-200">{value}</span>
    </div>
  );
}

function statusClass(status: string) {
  if (status === "available" || status === "ready") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (status === "unavailable") return "border-red-500/30 bg-red-500/10 text-red-100";
  if (status === "skipped" || status === "degraded") return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  if (status === "disabled") return "border-slate-700 bg-slate-800 text-slate-300";
  return "border-slate-700 bg-slate-800 text-slate-300";
}
