import { AlertTriangle, AppWindow, Images, PlaySquare, Server, UploadCloud } from "lucide-react";
import { mockApps, mockRuns, mockWorkers } from "../../lib/mock-data";
import { formatNumber } from "../../lib/format";
import { MetricCard } from "../ui/metric-card";

export function SystemMetrics() {
  const running = mockRuns.filter((run) => run.status === "running").length;
  const uploadPending = mockRuns.filter((run) => run.status === "upload_pending").length;
  const failed = mockRuns.filter((run) => run.status === "failed_low_yield" || run.status === "skipped_risk").length;
  const workerOnline = mockWorkers.filter((worker) => worker.state !== "stopped" && worker.state !== "failed").length;
  const validToday = mockRuns.reduce((total, run) => total + run.valid_total, 0);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      <MetricCard label="Apps" value={mockApps.length} detail="registered targets" icon={<AppWindow size={18} />} tone="blue" />
      <MetricCard label="Runs" value={mockRuns.length} detail={`${running} running now`} icon={<PlaySquare size={18} />} tone="green" />
      <MetricCard label="Upload Pending" value={uploadPending} detail="waiting manual upload" icon={<UploadCloud size={18} />} tone="amber" />
      <MetricCard label="Failed" value={failed} detail="low yield or risk skipped" icon={<AlertTriangle size={18} />} tone="red" />
      <MetricCard label="Workers Online" value={`${workerOnline}/${mockWorkers.length}`} detail="heartbeat visible" icon={<Server size={18} />} tone="slate" />
      <MetricCard label="Valid Images" value={formatNumber(validToday)} detail="mock today total" icon={<Images size={18} />} tone="blue" />
    </div>
  );
}
