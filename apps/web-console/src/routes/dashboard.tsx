import { ActiveRuns } from "../components/dashboard/active-runs";
import { CaptureHealth } from "../components/dashboard/capture-health";
import { SystemMetrics } from "../components/dashboard/system-metrics";
import { WorkerSummary } from "../components/dashboard/worker-summary";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";

export function DashboardRoute() {
  return (
    <div>
      <PageHeader title="系统控制中心" description="面向应用、任务、Worker、上传压力与采集健康度的运行总览。" />
      <SystemMetrics />
      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <Card title="活跃任务" eyebrow="任务控制">
          <ActiveRuns />
        </Card>
        <Card title="采集健康度" eyebrow="分桶结构">
          <CaptureHealth />
        </Card>
      </div>
      <div className="mt-4">
        <Card title="Worker 摘要" eyebrow="采集容量">
          <WorkerSummary />
        </Card>
      </div>
    </div>
  );
}
