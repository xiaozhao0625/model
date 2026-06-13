import type { WorkerRecord } from "../../lib/api-types";
import { formatDateTime } from "../../lib/format";
import { workerStateLabels, workerTypeLabels } from "../../lib/status";
import { Badge } from "../ui/badge";
import { WorkerCapabilityTags } from "./worker-capability-tags";

export function WorkerCard({ worker }: { worker: WorkerRecord }) {
  const online = worker.state !== "stopped" && worker.state !== "failed";
  return (
    <article className="rounded-[10px] border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-mono text-sm font-semibold text-slate-100">{worker.worker_id}</h3>
          <p className="mt-1 text-xs text-slate-500">{worker.machine_name || "未分配机器"}</p>
        </div>
        <Badge className={online ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-slate-600 bg-slate-800 text-slate-300"}>
          {online ? "在线" : "离线"}
        </Badge>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-slate-500">类型</dt>
          <dd className="mt-1 text-slate-200">{workerTypeLabels[worker.type] || worker.type}</dd>
        </div>
        <div>
          <dt className="text-slate-500">当前任务</dt>
          <dd className="mt-1 font-mono text-slate-200">{worker.current_run_id || workerStateLabels.idle}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-slate-500">最近心跳</dt>
          <dd className="mt-1 text-slate-300">{formatDateTime(worker.heartbeat)}</dd>
        </div>
      </dl>
      <div className="mt-4">
        <WorkerCapabilityTags capabilities={worker.capabilities} />
      </div>
    </article>
  );
}
