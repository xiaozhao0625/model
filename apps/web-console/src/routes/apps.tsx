import { useEffect, useState } from "react";
import { AppCard } from "../components/apps/app-card";
import { CreateAppForm } from "../components/apps/create-app-form";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { AppRecord } from "../lib/api-types";

export function AppsRoute() {
  const [apps, setApps] = useState<AppRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("正在从 Master API 读取应用库。");
  const [error, setError] = useState<string | null>(null);

  async function loadApps() {
    setLoading(true);
    try {
      const records = await apiClient.listApps();
      setApps(records);
      setError(null);
      setMessage(apiClient.isUsingMockFallback() ? "Master API 不可用，当前显示本地演示数据。" : "应用库已从 Master API 同步。");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setMessage("应用库读取失败。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadApps();
  }, []);

  async function handleCreate(app: AppRecord) {
    setError(null);
    try {
      const created = await apiClient.createApp(app);
      const refreshed = await apiClient.listApps();
      setApps(refreshed);
      setMessage(`已新建并持久化应用：${created.app_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setMessage("新建应用失败，后端未确认前不会加入列表。");
    }
  }

  return (
    <div>
      <PageHeader title="应用库" description="登记采集目标，并在创建任务前确认应用类型、平台和采集边界。" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card title="已登记应用" eyebrow="应用登记">
          {loading ? <p className="text-sm text-slate-500">加载中...</p> : null}
          {!loading && apps.length === 0 ? <p className="text-sm text-slate-500">暂无应用。</p> : null}
          <div className="grid gap-3 md:grid-cols-2">
            {apps.map((app) => (
              <AppCard key={app.app_id} app={app} />
            ))}
          </div>
        </Card>
        <Card title="新建应用" eyebrow="表单">
          <CreateAppForm onCreate={handleCreate} />
          <p className={error ? "mt-3 text-xs text-red-300" : "mt-3 text-xs text-slate-500"}>{error || message}</p>
        </Card>
      </div>
    </div>
  );
}
