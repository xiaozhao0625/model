import { useEffect, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ActionRecord, V3Health, V3RunRecord, V3Summary, V3TaskConfig } from "../lib/api-types";

export function V3DashboardRoute() {
  const [health, setHealth] = useState<V3Health | null>(null);
  const [defaults, setDefaults] = useState<V3TaskConfig | null>(null);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [summary, setSummary] = useState<V3Summary | null>(null);
  const [actions, setActions] = useState<V3ActionRecord[]>([]);
  const [message, setMessage] = useState("V3 observe_only is enabled by default; real click is disabled by default.");

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
    setMessage(`Created observe_only run: ${run.run_id}`);
    await load(run.run_id);
  }

  async function selectRun(runId: string) {
    setSelectedRunId(runId);
    await loadRunDetails(runId);
  }

  const latestAction = actions[actions.length - 1];

  return (
    <div>
      <PageHeader title="V3 OBS-OCR Console" description="Local capture, OCR, candidates, safety gate, and action audit." />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card title="Runtime State" eyebrow="V3">
          <div className="grid gap-3 md:grid-cols-3">
            <Metric label="V3 status" value={health?.status || "loading"} />
            <Metric label="OCR GPU" value={health?.ocr_gpu_ready ? "ready" : "not_ready"} />
            <Metric label="OCR performance" value={health?.ocr_performance_ready ? "ready" : "not_ready"} />
            <Metric label="OCR production" value={health?.ocr_production_ready ? "ready" : "not_ready"} />
            <Metric label="Input gateway" value={health?.input_gateway_ready ? "ready" : "not_ready"} />
            <Metric label="Cursor read" value={health?.cursor_read_ready ? "ready" : "not_ready"} />
            <Metric label="Mouse click" value={health?.mouse_click_ready ? "ready" : "not_ready"} />
            <Metric label="Desktop session" value={health?.same_desktop_session_ready ? "ready" : "not_ready"} />
            <Metric label="Integrity" value={health?.same_integrity_ready ? "ready" : "not_ready"} />
            <Metric label="Interactive desktop" value={health?.interactive_desktop_ready ? "ready" : "not_ready"} />
            <Metric label="Click backend" value={health?.click_backend || "unknown"} />
            <Metric label="Full auto" value={health?.full_auto_capture_ready ? "ready" : "not_ready"} />
            <Metric label="Runs" value={String(runs.length)} />
          </div>
          <Blockers blockers={[...(health?.readiness_blockers || []), ...(health?.input_gateway_blockers || [])]} />
          <button className="mt-4 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100 hover:bg-blue-500/10" onClick={() => void createObserveOnlyRun()}>
            Create observe_only run
          </button>
          <p className="mt-3 text-sm text-slate-400">{message}</p>
        </Card>

        <Card title="Models And OCR" eyebrow="providers">
          <ProviderList title="OCR" providers={health?.ocr || []} />
          <div className="mt-4">
            <ProviderList title="UI model" providers={health?.models || []} />
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card title="Recent V3 Runs" eyebrow="runs">
          <div className="grid gap-2">
            {runs.length === 0 ? <p className="text-sm text-slate-500">No V3 runs yet.</p> : null}
            {runs.map((run) => (
              <button
                key={run.run_id}
                className={`grid gap-2 rounded-lg border p-3 text-left md:grid-cols-[1.4fr_0.45fr_0.9fr_0.8fr] ${
                  run.run_id === selectedRunId ? "border-blue-500/60 bg-blue-950/20" : "border-slate-800 bg-slate-950"
                }`}
                onClick={() => void selectRun(run.run_id)}
              >
                <span className="font-mono text-xs text-slate-300">{run.run_id}</span>
                <span className="w-fit rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-300">{run.status}</span>
                <span className="text-sm text-slate-400">{run.config.app_name}</span>
                <span className="text-sm text-slate-500">observe_only={String(run.config.observe_only)}</span>
              </button>
            ))}
          </div>
        </Card>

        <Card title="Action Audit" eyebrow={selectedRunId || "no run selected"}>
          {summary ? (
            <>
              <div className="grid gap-3 md:grid-cols-3">
                <Metric label="accepted" value={String(summary.counts.accepted || 0)} />
                <Metric label="rejected" value={String(summary.counts.rejected || 0)} />
                <Metric label="actions" value={String(summary.counts.actions || actions.length)} />
                <Metric label="OCR production" value={summary.ocr_production_ready ? "ready" : "not_ready"} />
                <Metric label="Input gateway" value={summary.input_gateway_ready ? "ready" : "not_ready"} />
                <Metric label="Click backend" value={summary.click_backend || "unknown"} />
                <Metric label="Full auto" value={summary.full_auto_capture_ready ? "ready" : "not_ready"} />
                <Metric label="near duplicate" value={String(summary.near_duplicate_count || 0)} />
              </div>
              <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
                <h3 className="text-sm font-semibold text-slate-200">Duplicate Summary</h3>
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <Metric label="exact duplicate" value={String(summary.exact_duplicate_count || 0)} />
                  <Metric label="action representative" value={String(summary.action_representative_accepted_count || 0)} />
                  <Metric label="periodic static rejected" value={String(summary.periodic_static_rejected_count || 0)} />
                </div>
                <AuditRow label="accepted_by_ui_state_hint" value={formatRecord(summary.accepted_by_ui_state_hint)} />
                <AuditRow label="duplicate explanation report" value={summary.duplicate_explanation_report_path || "-"} />
              </div>
              <Blockers blockers={[...(summary.readiness_blockers || []), ...(summary.input_gateway_blockers || [])]} />
            </>
          ) : (
            <p className="text-sm text-slate-500">Select a V3 run to inspect action audit.</p>
          )}
          {latestAction ? (
            <div className="mt-4 grid gap-2 rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
              <AuditRow label="label" value={latestAction.label || "-"} />
              <AuditRow label="status" value={latestAction.result?.status || "-"} />
              <AuditRow label="reason" value={latestAction.result?.reason || "-"} />
              <AuditRow label="click_backend" value={latestAction.result?.click_backend || "-"} />
              <AuditRow label="blocked reason" value={String(latestAction.safety_result?.reason || latestAction.result?.rollback_reason || "-")} />
              <AuditRow label="source_candidate_id" value={latestAction.source_candidate_id || "-"} />
              <AuditRow label="before_image" value={latestAction.before_image || "-"} />
              <AuditRow label="after_image" value={latestAction.after_image || "-"} />
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">No action audit for this run yet.</p>
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
        {providers.map((provider) => (
          <div key={provider.provider} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
            <span className="text-sm text-slate-300">{provider.provider}</span>
            <span className="text-xs text-slate-500">
              {provider.status}
              {provider.enabled ? " / enabled" : " / disabled"}
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
    <div className="grid gap-2 md:grid-cols-[140px_1fr]">
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
  return <p className="mt-3 break-words font-mono text-xs text-amber-300">{blockers.join(", ")}</p>;
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
