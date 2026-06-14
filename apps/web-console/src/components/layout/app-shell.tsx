import { AlertTriangle, FileText, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
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
              <Card title="Runtime Notes" eyebrow="side panel">
                <div className="space-y-3 text-sm text-slate-400">
                  <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 text-emerald-300" size={17} />
                    <p>The console does not execute real mouse, keyboard, model, or capture actions by itself.</p>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="mt-0.5 text-amber-300" size={17} />
                    <p>Upload cleanup still requires operator confirmation before local files are removed.</p>
                  </div>
                  <div className="flex gap-3">
                    <FileText className="mt-0.5 text-blue-300" size={17} />
                    <p>Worker pages read live Master API data first. Demo fallback is shown only with an explicit API failure reason.</p>
                  </div>
                </div>
              </Card>
              <Card title="Live API" eyebrow="runtime source">
                <div className="space-y-3 text-sm text-slate-400">
                  <p>Worker status is loaded from the Master API endpoint.</p>
                  <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400">
                    {JSON.stringify({ endpoint: "/api/workers", source: "live_master_api" }, null, 2)}
                  </pre>
                </div>
              </Card>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
