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
      <MetricCard label="应用总数" value={mockApps.length} detail="已登记采集目标" icon={<AppWindow size={18} />} tone="blue" />
      <MetricCard label="任务总数" value={mockRuns.length} detail={`${running} 个正在运行`} icon={<PlaySquare size={18} />} tone="green" />
      <MetricCard label="待上传" value={uploadPending} detail="等待人工上传确认" icon={<UploadCloud size={18} />} tone="amber" />
      <MetricCard label="失败/跳过" value={failed} detail="低产失败或风险跳过" icon={<AlertTriangle size={18} />} tone="red" />
      <MetricCard label="Worker 在线" value={`${workerOnline}/${mockWorkers.length}`} detail="心跳可见" icon={<Server size={18} />} tone="slate" />
      <MetricCard label="有效截图" value={formatNumber(validToday)} detail="今日 mock 汇总" icon={<Images size={18} />} tone="blue" />
    </div>
  );
}
