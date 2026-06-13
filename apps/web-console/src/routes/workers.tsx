import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { WorkerCard } from "../components/workers/worker-card";
import { mockWorkers } from "../lib/mock-data";

export function WorkersRoute() {
  return (
    <div>
      <PageHeader title="Worker 监控" description="监控 Worker 能力、当前任务、心跳状态和各平台采集边界。" />
      <div className="mb-4 rounded-[10px] border border-blue-500/30 bg-blue-500/10 p-4 text-sm text-blue-100">
        Web Worker 合同：content_area_only=true。后续真实 Playwright 采集必须排除浏览器地址栏、标签栏和 Windows 任务栏。
      </div>
      <Card title="Worker 列表" eyebrow="采集节点">
        <div className="grid gap-3 md:grid-cols-2">
          {mockWorkers.map((worker) => (
            <WorkerCard key={worker.worker_id} worker={worker} />
          ))}
        </div>
      </Card>
    </div>
  );
}
