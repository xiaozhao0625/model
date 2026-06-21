import { Activity, Archive, FolderOpen, Gamepad2, Gauge, Images, ListPlus, ScrollText, Settings, Stethoscope, Wand2 } from "lucide-react";
import { NavLink } from "react-router-dom";

const primaryNavItems = [
  { to: "/v3", label: "控制台", icon: Wand2 },
  { to: "/v3/new", label: "新建采集", icon: ListPlus },
  { to: "/v3/current", label: "当前任务", icon: Gauge },
  { to: "/v3/gallery", label: "采集结果", icon: Images },
  { to: "/v3/actions", label: "运行审计", icon: ScrollText },
  { to: "/v3/game", label: "游戏采集", icon: Gamepad2 },
  { to: "/v3/reports", label: "报告中心", icon: Archive },
  { to: "/v3/status", label: "系统状态", icon: Stethoscope },
  { to: "/settings", label: "设置", icon: Settings }
];

const legacyNavItems = [
  { to: "/dashboard", label: "旧系统控制台" },
  { to: "/apps", label: "旧应用管理" },
  { to: "/runs", label: "旧任务中心" },
  { to: "/workers", label: "旧 Worker 监控" },
  { to: "/upload", label: "旧上传与清理" },
  { to: "/model-gateway", label: "旧模型网关" },
  { to: "/quality-reports", label: "旧质量报告" },
  { to: "/ocr-status", label: "旧 OCR 状态" },
  { to: "/behavior-candidates", label: "旧行为包候选" }
];

export function Sidebar() {
  return (
    <aside className="hidden min-h-[100dvh] w-64 shrink-0 border-r border-slate-800 bg-[#0B0F14] p-4 lg:block">
      <div className="flex items-center gap-3 rounded-[10px] border border-slate-800 bg-slate-900 p-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-300">
          <Activity size={20} />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-100">操作员采集台</p>
          <p className="text-xs text-slate-500">单机 V3 采集控制中心</p>
        </div>
      </div>
      <nav className="mt-6 space-y-1">
        {primaryNavItems.map((item) => (
          <SidebarLink key={item.to} to={item.to} label={item.label} icon={item.icon} end={item.to === "/v3"} />
        ))}
      </nav>
      <details className="mt-5 rounded-lg border border-slate-800 bg-slate-950 p-2">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-2 py-1 text-xs font-medium text-slate-400">
          <FolderOpen size={14} />
          高级调试
        </summary>
        <div className="mt-2 space-y-1">
          {legacyNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-md px-3 py-1.5 text-xs transition ${isActive ? "bg-slate-800 text-slate-100" : "text-slate-500 hover:bg-slate-900 hover:text-slate-200"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </details>
    </aside>
  );
}

function SidebarLink({ to, label, icon: Icon, end = false }: { to: string; label: string; icon: typeof Wand2; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
          isActive ? "border border-blue-500/30 bg-blue-500/10 text-blue-100" : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
        }`
      }
    >
      <Icon size={17} />
      {label}
    </NavLink>
  );
}
