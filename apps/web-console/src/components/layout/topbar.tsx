import { Database, RadioTower } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#0B0F14]/95 px-4 py-3 backdrop-blur md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">AI 截图平台系统控制台</h1>
          <p className="text-xs text-slate-500">采集任务、工具健康、模型状态与安全审计的单机控制台</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <ThemeToggle />
          <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-emerald-200">
            <RadioTower size={14} />
            API fallback 已就绪
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-300">
            <Database size={14} />
            SQLite 单机模式
          </span>
        </div>
      </div>
    </header>
  );
}
