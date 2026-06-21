import { MonitorCheck, RadioTower } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#0B0F14]/95 px-4 py-3 backdrop-blur md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">V3 单机采集控制台</h1>
          <p className="text-xs text-slate-500">V3 单机采集软件：任务、结果、审计、报告和系统状态集中操作</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <ThemeToggle />
          <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-emerald-200">
            <RadioTower size={14} />
            V3 接口状态见系统状态页
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-300">
            <MonitorCheck size={14} />
            本机操作员模式
          </span>
        </div>
      </div>
    </header>
  );
}
