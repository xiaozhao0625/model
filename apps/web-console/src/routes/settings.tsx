import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";

const settings = [
  ["MASTER_URL", import.meta.env.VITE_MASTER_API_URL || "http://localhost:8000"],
  ["MODEL_GATEWAY_URL", "proxied through Master API"],
  ["DATA_ROOT", "runs/master"],
  ["MODEL_ROOT", "models/"],
  ["current mode", import.meta.env.MODE || "development"],
  ["topology name", "single_node_dev"]
];

export function SettingsRoute() {
  return (
    <div>
      <PageHeader title="Settings" description="Read-only environment view. P8 does not write configuration or launch services." />
      <Card title="Runtime Configuration" eyebrow="read only">
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
