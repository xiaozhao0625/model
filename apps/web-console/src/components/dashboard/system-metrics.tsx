import { AlertTriangle, AppWindow, Images, PlaySquare, Server, UploadCloud } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "../../lib/api-client";
import type { WorkerRecord } from "../../lib/api-types";
import { formatNumber } from "../../lib/format";
import { mockApps, mockRuns } from "../../lib/mock-data";
import { MetricCard } from "../ui/metric-card";

export function SystemMetrics() {
  const [workers, setWorkers] = useState<WorkerRecord[]>([]);
  const [workerFallback, setWorkerFallback] = useState(false);
  const running = mockRuns.filter((run) => run.status === "running").length;
  const uploadPending = mockRuns.filter((run) => run.status === "upload_pending").length;
  const failed = mockRuns.filter((run) => run.status === "failed_low_yield" || run.status === "skipped_risk").length;
  const workerOnline = workers.filter((worker) => worker.state !== "stopped" && worker.state !== "failed").length;
  const validToday = mockRuns.reduce((total, run) => total + run.valid_total, 0);

  useEffect(() => {
    let active = true;

    apiClient.listWorkers().then((records) => {
      if (!active) {
        return;
      }
      setWorkers(records);
      setWorkerFallback(apiClient.isUsingMockFallback());
    });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      <MetricCard label="应用数" value={mockApps.length} detail="已登记采集目标" icon={<AppWindow size={18} />} tone="blue" />
      <MetricCard label="任务数" value={mockRuns.length} detail={`${running} 个运行中`} icon={<PlaySquare size={18} />} tone="green" />
      <MetricCard label="待上传" value={uploadPending} detail="等待人工确认" icon={<UploadCloud size={18} />} tone="amber" />
      <MetricCard label="失败/跳过" value={failed} detail="低产出或风险跳过" icon={<AlertTriangle size={18} />} tone="red" />
      <MetricCard label="在线 Worker" value={`${workerOnline}/${workers.length}`} detail={workerFallback ? "演示兜底数据" : "实时 Master API"} icon={<Server size={18} />} tone="slate" />
      <MetricCard label="有效截图" value={formatNumber(validToday)} detail="任务摘要统计" icon={<Images size={18} />} tone="blue" />
    </div>
  );
}
