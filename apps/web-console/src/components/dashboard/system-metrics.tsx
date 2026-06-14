import { AlertTriangle, AppWindow, Images, PlaySquare, Server, UploadCloud } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "../../lib/api-client";
import type { WorkerRecord } from "../../lib/api-types";
import { mockApps, mockRuns } from "../../lib/mock-data";
import { formatNumber } from "../../lib/format";
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
      <MetricCard label="Apps" value={mockApps.length} detail="Registered capture targets" icon={<AppWindow size={18} />} tone="blue" />
      <MetricCard label="Runs" value={mockRuns.length} detail={`${running} running`} icon={<PlaySquare size={18} />} tone="green" />
      <MetricCard label="Upload pending" value={uploadPending} detail="Waiting for confirmation" icon={<UploadCloud size={18} />} tone="amber" />
      <MetricCard label="Failed/skipped" value={failed} detail="Low-yield or risk-skipped runs" icon={<AlertTriangle size={18} />} tone="red" />
      <MetricCard
        label="Workers online"
        value={`${workerOnline}/${workers.length}`}
        detail={workerFallback ? "Demo fallback data" : "Live Master API"}
        icon={<Server size={18} />}
        tone="slate"
      />
      <MetricCard label="Valid images" value={formatNumber(validToday)} detail="Mock run summary" icon={<Images size={18} />} tone="blue" />
    </div>
  );
}
