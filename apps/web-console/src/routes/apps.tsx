import { useState } from "react";
import type { AppRecord } from "../lib/api-types";
import { apiClient } from "../lib/api-client";
import { mockApps } from "../lib/mock-data";
import { AppCard } from "../components/apps/app-card";
import { CreateAppForm } from "../components/apps/create-app-form";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";

export function AppsRoute() {
  const [apps, setApps] = useState<AppRecord[]>(mockApps);
  const [message, setMessage] = useState("Mock data loaded. API fallback is available.");

  async function handleCreate(app: AppRecord) {
    const created = await apiClient.createApp(app);
    setApps((current) => [created, ...current.filter((item) => item.app_id !== created.app_id)]);
    setMessage(`Created ${created.app_id}`);
  }

  return (
    <div>
      <PageHeader title="Apps Registry" description="Register target applications and keep target_min / target_max defaults visible before run creation." />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="Registered Apps" eyebrow="registry">
          <div className="grid gap-3 md:grid-cols-2">
            {apps.map((app) => (
              <AppCard key={app.app_id} app={app} />
            ))}
          </div>
        </Card>
        <Card title="Create App" eyebrow="form">
          <CreateAppForm onCreate={handleCreate} />
          <p className="mt-3 text-xs text-slate-500">{message}</p>
        </Card>
      </div>
    </div>
  );
}
