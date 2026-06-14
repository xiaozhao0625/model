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
              <Card title="运行提示" eyebrow="操作员侧栏">
                <div className="space-y-3 text-sm text-slate-400">
                  <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 text-emerald-300" size={17} />
                    <p>控制台本身不会直接执行鼠标、键盘、模型或采集动作。</p>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="mt-0.5 text-amber-300" size={17} />
                    <p>上传清理必须由操作员确认后才会删除本地文件。</p>
                  </div>
                  <div className="flex gap-3">
                    <FileText className="mt-0.5 text-blue-300" size={17} />
                    <p>Worker 页面优先读取实时 Master API；只有接口失败时才显示演示兜底。</p>
                  </div>
                </div>
              </Card>
              <Card title="调试信息" eyebrow="默认折叠">
                <details className="text-sm text-slate-400">
                  <summary className="cursor-pointer text-slate-200">查看运行态 API 来源</summary>
                  <div className="mt-3 space-y-3">
                    <p>Worker 状态来自 Master API 的实时接口。</p>
                    <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400">
                      {JSON.stringify({ endpoint: "/api/workers", source: "live_master_api" }, null, 2)}
                    </pre>
                  </div>
                </details>
              </Card>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}
