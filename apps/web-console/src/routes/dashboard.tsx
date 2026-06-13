import { ActiveRuns } from "../components/dashboard/active-runs";
import { CaptureHealth } from "../components/dashboard/capture-health";
import { SystemMetrics } from "../components/dashboard/system-metrics";
import { WorkerSummary } from "../components/dashboard/worker-summary";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";

export function DashboardRoute() {
  return (
    <div>
      <PageHeader title="Dashboard" description="Live operational overview for apps, runs, workers, upload pressure, and capture health." />
      <SystemMetrics />
      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <Card title="Active Runs" eyebrow="run control">
          <ActiveRuns />
        </Card>
        <Card title="Capture Health" eyebrow="bucket mix">
          <CaptureHealth />
        </Card>
      </div>
      <div className="mt-4">
        <Card title="Worker Summary" eyebrow="capacity">
          <WorkerSummary />
        </Card>
      </div>
    </div>
  );
}
