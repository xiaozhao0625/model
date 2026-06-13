import { mockWorkers } from "../../lib/mock-data";
import { capabilityLabels, workerStateLabels } from "../../lib/status";
import { Badge } from "../ui/badge";

export function WorkerSummary() {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {mockWorkers.map((worker) => (
        <div key={worker.worker_id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-mono text-sm text-slate-100">{worker.worker_id}</p>
              <p className="mt-1 text-xs text-slate-500">{worker.machine_name}</p>
            </div>
            <Badge className={worker.state === "stopped" ? "border-slate-600 bg-slate-700/20 text-slate-300" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"}>
              {workerStateLabels[worker.state] || worker.state}
            </Badge>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {worker.capabilities.slice(0, 4).map((capability) => (
              <Badge key={capability} className="border-slate-700 bg-slate-900 text-slate-400">
                {capabilityLabels[capability] || capability}
              </Badge>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
