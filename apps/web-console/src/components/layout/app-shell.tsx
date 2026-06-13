import { AlertTriangle, FileText, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { mockRunLogs } from "../../lib/mock-data";
import { Card } from "../ui/card";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[100dvh] bg-[#0B0F14] text-slate-100">
      <div className="flex">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Topbar />
          <div className="grid min-h-[calc(100dvh-65px)] grid-cols-1 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <main className="min-w-0">{children}</main>
            <aside className="space-y-4">
              <Card title="Operational Notes" eyebrow="right panel">
                <div className="space-y-3 text-sm text-slate-400">
                  <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 text-emerald-300" size={17} />
                    <p>AI actions return proposals only. No real mouse, keyboard, model, or capture tool is executed here.</p>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="mt-0.5 text-amber-300" size={17} />
                    <p>Upload cleanup requires manual Baidu Netdisk confirmation before local deletion.</p>
                  </div>
                  <div className="flex gap-3">
                    <FileText className="mt-0.5 text-blue-300" size={17} />
                    <p>Mock fallback keeps this console usable when the Master API is offline.</p>
                  </div>
                </div>
              </Card>
              <Card title="Recent Run Log" eyebrow="jsonl">
                <div className="space-y-3">
                  {mockRunLogs.map((entry) => (
                    <div key={`${entry.timestamp}-${entry.event}`} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                      <p className="font-mono text-xs text-blue-300">{entry.event}</p>
                      <p className="mt-1 text-xs text-slate-500">{entry.timestamp}</p>
                      <pre className="mt-2 overflow-x-auto text-xs text-slate-400">{JSON.stringify(entry.details, null, 2)}</pre>
                    </div>
                  ))}
                </div>
              </Card>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
