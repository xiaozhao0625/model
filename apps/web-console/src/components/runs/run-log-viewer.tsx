import type { RunLogEntry } from "../../lib/api-types";

export function RunLogViewer({ logs }: { logs: RunLogEntry[] }) {
  return (
    <div className="max-h-[360px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3">
      {logs.map((entry) => (
        <pre key={`${entry.timestamp}-${entry.event}`} className="mb-3 whitespace-pre-wrap text-xs leading-5 text-slate-400 last:mb-0">
          {JSON.stringify(entry, null, 2)}
        </pre>
      ))}
    </div>
  );
}
