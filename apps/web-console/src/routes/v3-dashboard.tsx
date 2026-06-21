import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ActionRecord, V3Health, V3RunRecord, V3Summary, V3TaskConfig } from "../lib/api-types";
import { labelStatus } from "../lib/labels";

export function V3DashboardRoute() {
  const [health, setHealth] = useState<V3Health | null>(null);
  const [defaults, setDefaults] = useState<V3TaskConfig | null>(null);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [summary, setSummary] = useState<V3Summary | null>(null);
  const [actions, setActions] = useState<V3ActionRecord[]>([]);
  const [message, setMessage] = useState("V3 默认仅观察（observe_only），真实点击默认关闭。");

  async function load(nextSelectedRunId = selectedRunId) {
    const [nextHealth, nextDefaults, nextRuns] = await Promise.all([apiClient.getV3Health(), apiClient.getV3Defaults(), apiClient.listV3Runs()]);
    const activeRunId = nextSelectedRunId || nextRuns[0]?.run_id || null;
    setHealth(nextHealth);
    setDefaults(nextDefaults);
    setRuns(nextRuns);
    setSelectedRunId(activeRunId);
    if (activeRunId) {
      await loadRunDetails(activeRunId);
    } else {
      setSummary(null);
      setActions([]);
    }
  }

  async function loadRunDetails(runId: string) {
    const [nextSummary, nextActions] = await Promise.all([apiClient.getV3Summary(runId), apiClient.getV3Actions(runId)]);
    setSummary(nextSummary);
    setActions(nextActions);
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
    setMessage(`已创建仅观察任务：${run.run_id}`);
    await load(run.run_id);
  }

  async function selectRun(runId: string) {
    setSelectedRunId(runId);
    await loadRunDetails(runId);
  }

  const latestAction = actions[actions.length - 1];

  return (
    <div>
      <PageHeader title="V3 OBS-OCR 采集控制台" description="本地截图采集、OCR、候选点、安全门、动作审计与重复帧报告。" />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card title="运行状态" eyebrow="V3">
          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="V3 状态（status）" value={labelStatus(health?.status)} />
            <Metric label="OCR GPU 就绪（ocr_gpu_ready）" value={labelStatus(health?.ocr_gpu_ready)} />
            <Metric label="OCR 性能就绪（ocr_performance_ready）" value={labelStatus(health?.ocr_performance_ready)} />
            <Metric label="OCR 生产就绪（ocr_production_ready）" value={labelStatus(health?.ocr_production_ready)} />
            <Metric label="输入网关就绪（input_gateway_ready）" value={labelStatus(health?.input_gateway_ready)} />
            <Metric label="光标读取（cursor_read_ready）" value={labelStatus(health?.cursor_read_ready)} />
            <Metric label="鼠标点击（mouse_click_ready）" value={labelStatus(health?.mouse_click_ready)} />
            <Metric label="桌面会话（same_desktop_session_ready）" value={labelStatus(health?.same_desktop_session_ready)} />
            <Metric label="权限完整性（same_integrity_ready）" value={labelStatus(health?.same_integrity_ready)} />
            <Metric label="交互桌面（interactive_desktop_ready）" value={labelStatus(health?.interactive_desktop_ready)} />
            <Metric label="点击后端（click_backend）" value={health?.click_backend || "未知"} />
            <Metric label="完整自动采集（full_auto_capture_ready）" value={labelStatus(health?.full_auto_capture_ready)} />
            <Metric label="任务数（runs）" value={String(runs.length)} />
          </div>
          <Blockers blockers={[...(health?.readiness_blockers || []), ...(health?.input_gateway_blockers || [])]} />
          <button className="mt-4 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100 hover:bg-blue-500/10" onClick={() => void createObserveOnlyRun()}>
            创建仅观察任务
          </button>
          <p className="mt-3 text-sm text-slate-400">{message}</p>
        </Card>

        <Card title="模型与 OCR" eyebrow="providers">
          <ProviderList title="OCR 状态" providers={health?.ocr || []} />
          <div className="mt-4">
            <ProviderList title="UI 模型状态（ShowUI）" providers={health?.models || []} />
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card title="最近 V3 任务" eyebrow="runs">
          <div className="grid gap-2">
            {runs.length === 0 ? <p className="text-sm text-slate-500">暂无 V3 任务。</p> : null}
            {runs.map((run) => (
              <button
                key={run.run_id}
                className={`grid gap-2 rounded-lg border p-3 text-left md:grid-cols-[1.4fr_0.45fr_0.9fr_0.8fr] ${
                  run.run_id === selectedRunId ? "border-blue-500/60 bg-blue-950/20" : "border-slate-800 bg-slate-950"
                }`}
                onClick={() => void selectRun(run.run_id)}
              >
                <span className="font-mono text-xs text-slate-300">{run.run_id}</span>
                <span className="w-fit rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-300">{labelStatus(run.status)}</span>
                <span className="text-sm text-slate-400">{run.config.app_name}</span>
                <span className="text-sm text-slate-500">仅观察（observe_only）={String(run.config.observe_only)}</span>
              </button>
            ))}
          </div>
        </Card>

        <Card title="动作审计" eyebrow={selectedRunId || "未选择任务"}>
          {summary ? (
            <>
              <div className="grid gap-3 md:grid-cols-3">
                <Metric label="合格（accepted）" value={String(summary.counts.accepted || 0)} />
                <Metric label="拒绝（rejected）" value={String(summary.counts.rejected || 0)} />
                <Metric label="动作（actions）" value={String(summary.counts.actions || actions.length)} />
                <Metric label="OCR 生产就绪（ocr_production_ready）" value={labelStatus(summary.ocr_production_ready)} />
                <Metric label="输入网关就绪（input_gateway_ready）" value={labelStatus(summary.input_gateway_ready)} />
                <Metric label="点击后端（click_backend）" value={summary.click_backend || "未知"} />
                <Metric label="完整自动采集（full_auto_capture_ready）" value={labelStatus(summary.full_auto_capture_ready)} />
                <Metric label="近重复（near_duplicate）" value={String(summary.near_duplicate_count || 0)} />
              </div>
              <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
                <h3 className="text-sm font-semibold text-slate-200">重复帧摘要（Duplicate Summary）</h3>
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <Metric label="精确重复（exact_duplicate）" value={String(summary.exact_duplicate_count || 0)} />
                  <Metric label="动作代表帧（action representative）" value={String(summary.action_representative_accepted_count || 0)} />
                  <Metric label="周期静态拒绝（periodic static rejected）" value={String(summary.periodic_static_rejected_count || 0)} />
                </div>
                <AuditRow label="界面状态分布（accepted_by_ui_state_hint）" value={formatRecord(summary.accepted_by_ui_state_hint)} />
                <AuditRow label="重复帧解释报告（duplicate explanation report）" value={summary.duplicate_explanation_report_path || "-"} />
              </div>
              <Blockers blockers={[...(summary.readiness_blockers || []), ...(summary.input_gateway_blockers || [])]} />
            </>
          ) : (
            <p className="text-sm text-slate-500">请选择一个 V3 任务查看动作审计。</p>
          )}
          {latestAction ? (
            <div className="mt-4 grid gap-2 rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
              <AuditRow label="标签（label）" value={latestAction.label || "-"} />
              <AuditRow label="状态（status）" value={latestAction.result?.status || "-"} />
              <AuditRow label="原因（reason）" value={latestAction.result?.reason || "-"} />
              <AuditRow label="点击后端（click_backend）" value={latestAction.result?.click_backend || "-"} />
              <AuditRow label="阻断原因（blocked reason）" value={String(latestAction.safety_result?.reason || latestAction.result?.rollback_reason || "-")} />
              <AuditRow label="候选来源（source_candidate_id）" value={latestAction.source_candidate_id || "-"} />
              <AuditRow label="点击前截图（before_image）" value={latestAction.before_image || "-"} />
              <AuditRow label="点击后截图（after_image）" value={latestAction.after_image || "-"} />
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">当前任务暂无动作审计记录。</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function ProviderList({ title, providers }: { title: string; providers: V3Health["ocr"] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      <div className="mt-2 grid gap-2">
        {providers.length === 0 ? <p className="text-sm text-slate-500">不可用/未配置。</p> : null}
        {providers.map((provider) => (
          <div key={provider.provider} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
            <span className="text-sm text-slate-300">{provider.provider}</span>
            <span className="text-xs text-slate-500">
              {labelStatus(provider.status)}
              {provider.enabled ? " / 已启用" : " / 已禁用"}
            </span>
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

function AuditRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-2 md:grid-cols-[180px_1fr]">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="break-all font-mono text-xs text-slate-300">{value}</span>
    </div>
  );
}

function formatRecord(record?: Record<string, number>) {
  if (!record || Object.keys(record).length === 0) {
    return "-";
  }
  return Object.entries(record)
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");
}

function Blockers({ blockers }: { blockers: string[] }) {
  if (!blockers.length) {
    return null;
  }
  return <p className="mt-3 break-words font-mono text-xs text-amber-300">阻塞项：{blockers.join(", ")}</p>;
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
    max_actions: 5,
    safety_mode: "strict",
    observe_only: true,
    must_have_text: false
  };
}
