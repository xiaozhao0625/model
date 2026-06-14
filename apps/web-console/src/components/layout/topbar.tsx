import { Database, RadioTower } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "../../lib/api-client";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  const [apiLabel, setApiLabel] = useState("Master API：检查中");
  const [apiFallback, setApiFallback] = useState(false);
  const [dbLabel, setDbLabel] = useState("数据库：未知");
  const [redisLabel, setRedisLabel] = useState("Redis：未知");

  useEffect(() => {
    let active = true;

    apiClient.getHealth().then((health) => {
      if (!active) {
        return;
      }
      const fallback = apiClient.isUsingMockFallback();
      const databaseBackend = typeof health.database_backend === "string" ? health.database_backend : "unknown";
      const status = typeof health.status === "string" ? health.status : "unknown";
      const redisStatus = typeof health.redis_status === "string" ? health.redis_status : "unknown";
      const fallbackError = apiClient.getFallbackError();
      setApiFallback(fallback);
      setApiLabel(fallback ? `数据源：本地演示（${fallbackError?.failed_endpoint || "未知接口"}）` : `Master API：${status === "ok" ? "正常" : status}`);
      setDbLabel(`数据库：${databaseBackend === "postgresql" ? "PostgreSQL" : databaseBackend}`);
      setRedisLabel(`Redis：${redisStatus === "available" ? "正常" : redisStatus}`);
    });

    return () => {
      active = false;
    };
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#0B0F14]/95 px-4 py-3 backdrop-blur md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">多类型应用自动截图采集平台</h1>
          <p className="text-xs text-slate-500">任务、Worker、上传清理、质量与安全边界</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <ThemeToggle />
          <span
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 ${
              apiFallback ? "border-amber-500/30 bg-amber-500/10 text-amber-200" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
            }`}
          >
            <RadioTower size={14} />
            {apiLabel}
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-300">
            <Database size={14} />
            {dbLabel}
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-emerald-200">
            {redisLabel}
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-blue-100">
            数据源：实时
          </span>
        </div>
      </div>
    </header>
  );
}
