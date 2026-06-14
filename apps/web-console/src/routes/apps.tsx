import { useState } from "react";
import { AppCard } from "../components/apps/app-card";
import { CreateAppForm } from "../components/apps/create-app-form";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { AppRecord } from "../lib/api-types";
import { mockApps } from "../lib/mock-data";

export function AppsRoute() {
  const [apps, setApps] = useState<AppRecord[]>(mockApps);
  const [message, setMessage] = useState("已加载本地演示数据；实时 API 不可用时会使用兜底。");

  async function handleCreate(app: AppRecord) {
    const created = await apiClient.createApp(app);
    setApps((current) => [created, ...current.filter((item) => item.app_id !== created.app_id)]);
    setMessage(`已新建应用：${created.app_id}`);
  }

  return (
    <div>
      <PageHeader title="应用库" description="登记采集目标，并在创建任务前确认 target_min / target_max 等关键配置。" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="已登记应用" eyebrow="应用登记">
          <div className="grid gap-3 md:grid-cols-2">
            {apps.map((app) => (
              <AppCard key={app.app_id} app={app} />
            ))}
          </div>
        </Card>
        <Card title="新建应用" eyebrow="表单">
          <CreateAppForm onCreate={handleCreate} />
          <p className="mt-3 text-xs text-slate-500">{message}</p>
        </Card>
      </div>
    </div>
  );
}
