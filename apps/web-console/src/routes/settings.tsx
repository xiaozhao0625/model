import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";

const settings = [
  ["API_BASE_URL", import.meta.env.VITE_MASTER_API_URL || import.meta.env.VITE_API_BASE_URL || "/api"],
  ["MODEL_GATEWAY_URL", "通过 Master API 代理"],
  ["DATA_ROOT", "runs/master"],
  ["MODEL_ROOT", "models/"],
  ["当前模式", import.meta.env.MODE || "development"],
  ["拓扑名称", "single_node_dev"]
];

export function SettingsRoute() {
  return (
    <div>
      <PageHeader title="系统设置" description="只读环境配置视图。P8 不写入配置，也不启动服务。" />
      <Card title="运行配置" eyebrow="只读">
        <div className="grid gap-3">
          {settings.map(([key, value]) => (
            <div key={key} className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950 p-3 md:grid-cols-[220px_1fr]">
              <span className="font-mono text-xs text-slate-500">{key}</span>
              <span className="text-sm text-slate-200">{value}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
