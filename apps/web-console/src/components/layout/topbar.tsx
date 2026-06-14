import { Database, RadioTower } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "../../lib/api-client";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  const [apiLabel, setApiLabel] = useState("Checking Master API");
  const [apiFallback, setApiFallback] = useState(false);
  const [dbLabel, setDbLabel] = useState("DB: unknown");

  useEffect(() => {
    let active = true;

    apiClient.getHealth().then((health) => {
      if (!active) {
        return;
      }
      const fallback = apiClient.isUsingMockFallback();
      const databaseBackend = typeof health.database_backend === "string" ? health.database_backend : "unknown";
      const status = typeof health.status === "string" ? health.status : "unknown";
      setApiFallback(fallback);
      setApiLabel(fallback ? "API fallback active" : `Master API ${status}`);
      setDbLabel(`Master DB: ${databaseBackend}`);
    });

    return () => {
      active = false;
    };
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#0B0F14]/95 px-4 py-3 backdrop-blur md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">AI Screenshot Platform Control Center</h1>
          <p className="text-xs text-slate-500">Capture jobs, workers, upload cleanup, and model safety controls</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
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
        </div>
      </div>
    </header>
  );
}
