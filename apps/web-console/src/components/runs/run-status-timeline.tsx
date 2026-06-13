import type { RunStatus } from "../../lib/api-types";
import { lifecycleSteps, statusLabels } from "../../lib/status";

export function RunStatusTimeline({ status }: { status: RunStatus }) {
  const activeIndex = lifecycleSteps.indexOf(status);
  return (
    <ol className="space-y-3">
      {lifecycleSteps.map((step, index) => {
        const active = index <= activeIndex;
        return (
          <li key={step} className="flex items-center gap-3">
            <span className={`h-2.5 w-2.5 rounded-full ${active ? "bg-blue-400" : "bg-slate-700"}`} />
            <span className={active ? "text-sm text-slate-100" : "text-sm text-slate-500"}>{statusLabels[step]}</span>
          </li>
        );
      })}
    </ol>
  );
}
