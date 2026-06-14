import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { WorkerCard } from "../components/workers/worker-card";
import { apiClient } from "../lib/api-client";
import type { WorkerRecord } from "../lib/api-types";

interface MasterNodeHealth {
  database_backend?: string;
  db_backend?: string;
  postgres_status?: string;
  redis_status?: string;
  redis_backend?: string;
  master_node?: {
    id?: string;
    role?: string;
    ip?: string;
    master_api?: string;
    web_console?: string;
    postgresql?: string;
    redis?: string;
  };
}

const workerOrder = ["worker_pc_game_w1", "worker_pc_app_web_w2", "worker_android_w3"];

export function WorkersRoute() {
  const [workers, setWorkers] = useState<WorkerRecord[]>([]);
  const [masterHealth, setMasterHealth] = useState<MasterNodeHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [fallbackDetail, setFallbackDetail] = useState<string>("");

  useEffect(() => {
    let active = true;

    Promise.all([apiClient.listWorkers(), apiClient.getHealth() as Promise<MasterNodeHealth>])
      .then(([records, health]) => {
        if (!active) {
          return;
        }
        setWorkers(sortWorkers(records));
        setMasterHealth(health);
        setUsingFallback(apiClient.isUsingMockFallback());
        const fallbackError = apiClient.getFallbackError();
        setFallbackDetail(
          fallbackError
            ? `${fallbackError.api_base_url}${fallbackError.failed_endpoint}: ${fallbackError.status || "network"} ${fallbackError.error}`
            : ""
        );
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
          {fallbackDetail ? <span className="mt-1 block font-mono text-xs text-amber-200">{fallbackDetail}</span> : null}
        </div>
      ) : null}
      <MasterNodeCard health={masterHealth} workerCount={workers.length} />
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

function sortWorkers(records: WorkerRecord[]): WorkerRecord[] {
  return [...records].sort((left, right) => {
    const leftIndex = workerOrder.indexOf(left.worker_id);
    const rightIndex = workerOrder.indexOf(right.worker_id);
    return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex);
  });
}

function MasterNodeCard({ health, workerCount }: { health: MasterNodeHealth | null; workerCount: number }) {
  const node = health?.master_node || {};
  const dbBackend = health?.database_backend || health?.db_backend || "unknown";
  const postgresStatus = health?.postgres_status || node.postgresql || "unknown";
  const redisStatus = health?.redis_status || node.redis || "unknown";

  return (
    <Card title="M0-MASTER" eyebrow="Master / Control Plane">
      <div className="grid gap-3 text-sm md:grid-cols-3">
        <StatusField label="Role" value={node.role || "Master / PostgreSQL / Redis / Web Console / Model Gateway"} />
        <StatusField label="IP" value={node.ip || "192.168.1.18"} mono />
        <StatusField label="Master API" value={node.master_api || "ok"} />
        <StatusField label="DB backend" value={dbBackend} tone={dbBackend === "postgresql" ? "good" : "warn"} />
        <StatusField label="PostgreSQL" value={postgresStatus} tone={postgresStatus === "available" ? "good" : "warn"} />
        <StatusField label="Redis" value={`${redisStatus}${health?.redis_backend ? ` (${health.redis_backend})` : ""}`} tone={redisStatus === "available" ? "good" : "warn"} />
        <StatusField label="Web Console" value={node.web_console || "ok"} />
        <StatusField label="Worker count" value={String(workerCount)} mono />
        <StatusField label="Node type" value="Control plane, not a Worker" />
      </div>
    </Card>
  );
}

function StatusField({ label, value, mono = false, tone = "neutral" }: { label: string; value: string; mono?: boolean; tone?: "good" | "warn" | "neutral" }) {
  const valueClass =
    tone === "good" ? "text-emerald-200" : tone === "warn" ? "text-amber-200" : "text-slate-200";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`mt-1 ${mono ? "font-mono" : ""} ${valueClass}`}>{value}</dd>
    </div>
  );
}
