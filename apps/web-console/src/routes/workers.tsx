import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { WorkerCard } from "../components/workers/worker-card";
import { mockWorkers } from "../lib/mock-data";

export function WorkersRoute() {
  return (
    <div>
      <PageHeader title="Worker Monitor" description="Monitor worker capabilities, current assignment, heartbeat, and platform-specific capture boundaries." />
      <div className="mb-4 rounded-[10px] border border-blue-500/30 bg-blue-500/10 p-4 text-sm text-blue-100">
        Web Worker contract: content_area_only=true. Future real Playwright capture must exclude address bar, tabs, and Windows taskbar.
      </div>
      <Card title="Workers" eyebrow="fleet">
        <div className="grid gap-3 md:grid-cols-2">
          {mockWorkers.map((worker) => (
            <WorkerCard key={worker.worker_id} worker={worker} />
          ))}
        </div>
      </Card>
    </div>
  );
}
