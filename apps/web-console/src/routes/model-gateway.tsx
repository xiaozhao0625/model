import { Bot, ShieldX } from "lucide-react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { DataTable } from "../components/ui/table";
import { mockModelProviders } from "../lib/mock-data";

export function ModelGatewayRoute() {
  const blocked = mockModelProviders.reduce((total, provider) => total + provider.blocked_count, 0);
  return (
    <div>
      <PageHeader title="Model Gateway" description="Mock and stub provider visibility, capability declarations, safety blocks, and recent audit state. No real model is loaded here." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Provider Registry" eyebrow="capabilities">
          <DataTable columns={["provider", "type", "enabled", "scene", "ground", "act"]}>
            {mockModelProviders.map((provider) => (
              <tr key={provider.provider_name}>
                <td className="font-mono text-blue-300">{provider.provider_name}</td>
                <td className="text-slate-300">{provider.provider_type}</td>
                <td>
                  <Badge className={provider.enabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-slate-700 bg-slate-800 text-slate-300"}>
                    {String(provider.enabled)}
                  </Badge>
                </td>
                <td className="text-slate-400">{String(provider.supports_scene_classify)}</td>
                <td className="text-slate-400">{String(provider.supports_ground)}</td>
                <td className="text-slate-400">{String(provider.supports_act)}</td>
              </tr>
            ))}
          </DataTable>
        </Card>
        <Card title="Safety Audit" eyebrow="model_gateway.log">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
              <ShieldX className="text-red-300" size={22} />
              <p className="mt-3 text-2xl font-semibold text-red-100">{blocked}</p>
              <p className="mt-1 text-sm text-red-100/70">blocked high-risk intents</p>
            </div>
            <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
              <Bot className="text-blue-300" size={22} />
              <p className="mt-3 text-2xl font-semibold text-blue-100">mock only</p>
              <p className="mt-1 text-sm text-blue-100/70">real models are not connected in P8</p>
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
