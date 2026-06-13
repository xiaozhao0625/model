import type { RunSummary } from "../../lib/api-types";
import { toJson } from "../../lib/format";

export function RunSummaryPanel({ summary }: { summary: RunSummary }) {
  return <pre className="max-h-[360px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs leading-5 text-slate-400">{toJson(summary)}</pre>;
}
