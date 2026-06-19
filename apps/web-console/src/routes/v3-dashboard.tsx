import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3Health, V3RunRecord, V3TaskConfig } from "../lib/api-types";

export function V3DashboardRoute() {
  const [health, setHealth] = useState<V3Health | null>(null);
  const [defaults, setDefaults] = useState<V3TaskConfig | null>(null);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [message, setMessage] = useState("V3 observe_only 默认开启，真实点击默认关闭。");

  async function load() {
    const [nextHealth, nextDefaults, nextRuns] = await Promise.all([apiClient.getV3Health(), apiClient.getV3Defaults(), apiClient.listV3Runs()]);
    setHealth(nextHealth);
    setDefaults(nextDefaults);
    setRuns(nextRuns);
  }

  useEffect(() => {
    void load();
  }, []);

  async function createObserveOnlyRun() {
    const config = {
      ...(defaults || fallbackDefaults()),
      app_name: `v3_manual_${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "")}`,
      observe_only: true,
      enable_auto_click: false
    };
    const run = await apiClient.createV3Run({ config });
    setMessage(`已创建 observe_only run：${run.run_id}`);
    await load();
  }

  return (
    <div>
      <PageHeader title="V3 OBS-OCR 通用采集器" description="本地轻量闭环：截图、OCR、UI 模型候选、安全门与 observe_only 审核。" />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card title="运行状态" eyebrow="V3">
          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="V3 状态" value={health?.status || "loading"} />
            <Metric label="完整自动模式" value={health?.complete_auto_mode_ready ? "ready" : "not_ready"} />
            <Metric label="任务数" value={String(runs.length)} />
          </div>
          <button className="mt-4 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100 hover:bg-blue-500/10" onClick={() => void createObserveOnlyRun()}>
            创建 observe_only 任务
          </button>
          <p className="mt-3 text-sm text-slate-400">{message}</p>
        </Card>

        <Card title="模型与 OCR" eyebrow="providers">
          <ProviderList title="OCR" providers={health?.ocr || []} />
          <div className="mt-4">
            <ProviderList title="UI 模型" providers={health?.models || []} />
          </div>
        </Card>
      </div>

      <Card title="最近 V3 Runs" eyebrow="runs" className="mt-4">
        <div className="grid gap-2">
          {runs.length === 0 ? <p className="text-sm text-slate-500">暂无 V3 run。</p> : null}
          {runs.map((run) => (
            <div key={run.run_id} className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950 p-3 md:grid-cols-[1.5fr_0.5fr_1fr_1fr]">
              <span className="font-mono text-xs text-slate-300">{run.run_id}</span>
              <span className="w-fit rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-300">{run.status}</span>
              <span className="text-sm text-slate-400">{run.config.app_name}</span>
              <span className="text-sm text-slate-500">observe_only={String(run.config.observe_only)}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ProviderList({ title, providers }: { title: string; providers: V3Health["ocr"] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      <div className="mt-2 grid gap-2">
        {providers.map((provider) => (
          <div key={provider.provider} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
            <span className="text-sm text-slate-300">{provider.provider}</span>
            <span className="text-xs text-slate-500">{provider.status}{provider.enabled ? " / enabled" : " / disabled"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function fallbackDefaults(): V3TaskConfig {
  return {
    app_name: "manual_target",
    app_type: "auto",
    target_language: "zh",
    capture_source: "folder_watch",
    capture_interval_ms: 1000,
    save_root: "runs/v3",
    enable_ocr: true,
    enable_ui_model: true,
    enable_auto_click: false,
    enable_game_explorer: false,
    delete_rejected: false,
    max_images: 100,
    safety_mode: "strict",
    observe_only: true,
    must_have_text: false
  };
}
