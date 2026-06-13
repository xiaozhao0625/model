import { Activity, AppWindow, Bot, Gauge, HardDriveUpload, PlaySquare, Settings, Server } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "系统控制中心", icon: Gauge },
  { to: "/apps", label: "应用库", icon: AppWindow },
  { to: "/runs", label: "任务控制中心", icon: PlaySquare },
  { to: "/workers", label: "Worker 监控", icon: Server },
  { to: "/upload", label: "上传与清理", icon: HardDriveUpload },
  { to: "/model-gateway", label: "模型网关", icon: Bot },
  { to: "/settings", label: "系统设置", icon: Settings }
];

export function Sidebar() {
  return (
    <aside className="hidden min-h-[100dvh] w-64 shrink-0 border-r border-slate-800 bg-[#0B0F14] p-4 lg:block">
      <div className="flex items-center gap-3 rounded-[10px] border border-slate-800 bg-slate-900 p-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-300">
          <Activity size={20} />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-100">AI 截图平台</p>
          <p className="text-xs text-slate-500">系统控制中心</p>
        </div>
      </div>
      <nav className="mt-6 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? "border border-blue-500/30 bg-blue-500/10 text-blue-100"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                }`
              }
            >
              <Icon size={17} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
