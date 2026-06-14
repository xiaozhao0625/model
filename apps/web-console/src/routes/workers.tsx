import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { WorkerCard } from "../components/workers/worker-card";
import { apiClient } from "../lib/api-client";
import type { WorkerRecord } from "../lib/api-types";

export function WorkersRoute() {
  const [workers, setWorkers] = useState<WorkerRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    let active = true;

    apiClient
      .listWorkers()
      .then((records) => {
        if (!active) {
          return;
        }
        setWorkers(records);
        setUsingFallback(apiClient.isUsingMockFallback());
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div>
      <PageHeader
        title="Worker Monitor"
        description="Live worker capabilities, heartbeat state, assigned work, and platform boundaries from the Master API."
      />
      <div className="mb-4 rounded-[10px] border border-blue-500/30 bg-blue-500/10 p-4 text-sm text-blue-100">
        Web worker contract: content_area_only=true. Browser chrome, tabs, address bars, and the Windows taskbar stay outside valid captures.
      </div>
      {usingFallback ? (
        <div className="mb-4 rounded-[10px] border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          Worker data is using local demo fallback because the live Master API request failed.
        </div>
      ) : null}
      <Card title="Worker List" eyebrow="Live collection nodes">
        {loading ? (
          <p className="text-sm text-slate-400">Loading live workers from {apiClient.getBaseUrl()}...</p>
        ) : workers.length === 0 ? (
          <p className="text-sm text-slate-400">No workers reported by the Master API.</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {workers.map((worker) => (
              <WorkerCard key={worker.worker_id} worker={worker} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
