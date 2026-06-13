import type { AppRecord } from "../../lib/api-types";
import { Badge } from "../ui/badge";

export function AppCard({ app }: { app: AppRecord }) {
  return (
    <article className="rounded-[10px] border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-100">{app.name}</h3>
          <p className="mt-1 font-mono text-xs text-slate-500">{app.app_id}</p>
        </div>
        <Badge className="border-blue-500/30 bg-blue-500/10 text-blue-200">{app.type}</Badge>
      </div>
      <p className="mt-4 text-sm text-slate-400">Platform: {app.platform}</p>
    </article>
  );
}
