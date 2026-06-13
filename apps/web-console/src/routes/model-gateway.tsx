import { Bot, ShieldX } from "lucide-react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { mockModelProviders } from "../lib/mock-data";
import { providerTypeLabels } from "../lib/status";

export function ModelGatewayRoute() {
  const blocked = mockModelProviders.reduce((total, provider) => total + provider.blocked_count, 0);
  return (
    <div>
      <PageHeader title="模型网关" description="展示 mock/stub provider、能力声明、安全拦截和最近审计状态。本阶段不加载真实模型。" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Provider 注册表" eyebrow="能力声明">
          <DataTable columns={["provider", "类型", "启用", "场景识别", "定位", "动作建议"]}>
            {mockModelProviders.map((provider) => (
              <tr key={provider.provider_name}>
                <td className="font-mono text-blue-300">{provider.provider_name}</td>
                <td className="text-slate-300">{providerTypeLabels[provider.provider_type] || provider.provider_type}</td>
                <td>
                  <Badge className={provider.enabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-slate-700 bg-slate-800 text-slate-300"}>
                    {provider.enabled ? "启用" : "停用"}
                  </Badge>
                </td>
                <td className="text-slate-400">{provider.supports_scene_classify ? "支持" : "不支持"}</td>
                <td className="text-slate-400">{provider.supports_ground ? "支持" : "不支持"}</td>
                <td className="text-slate-400">{provider.supports_act ? "支持" : "不支持"}</td>
              </tr>
            ))}
          </DataTable>
        </Card>
        <Card title="安全审计" eyebrow="model_gateway.log">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
              <ShieldX className="text-red-300" size={22} />
              <p className="mt-3 text-2xl font-semibold text-red-100">{blocked}</p>
              <p className="mt-1 text-sm text-red-100/70">已拦截高风险意图</p>
            </div>
            <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
              <Bot className="text-blue-300" size={22} />
              <p className="mt-3 text-2xl font-semibold text-blue-100">仅 mock</p>
              <p className="mt-1 text-sm text-blue-100/70">P8 不连接真实模型</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {mockModelProviders.map((provider) => (
              <div key={provider.provider_name} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="font-mono text-xs text-slate-300">{provider.provider_name}</p>
                <p className="mt-1 text-sm text-slate-500">{provider.last_event}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
