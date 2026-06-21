import { Activity, AlertTriangle, CheckCircle2, MousePointer2, ShieldCheck, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3Health } from "../lib/api-types";
import { labelStatus } from "../lib/labels";

type LoadState = {
  health: V3Health | null;
  modelHealth: V3Health | null;
  actionHealth: Record<string, unknown> | null;
  error: string | null;
};

export function ToolHealthRoute() {
  const [state, setState] = useState<LoadState>({ health: null, modelHealth: null, actionHealth: null, error: null });

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [health, modelHealth, actionHealth] = await Promise.all([apiClient.getV3Health(), apiClient.getV3ModelHealth(), apiClient.getV3ActionHealth()]);
      setState({ health, modelHealth, actionHealth, error: null });
    } catch (error) {
      setState({ health: null, modelHealth: null, actionHealth: null, error: `接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}` });
    }
  }

  const health = state.health;
  const actionHealth = state.actionHealth || {};
  const blockers = useMemo(() => [...(health?.readiness_blockers || []), ...(health?.input_gateway_blockers || [])], [health]);
  const showuiReady = Boolean((state.modelHealth?.models || health?.models || []).some((item) => item.provider === "showui" && item.status === "ready" && item.enabled));
  const performance = health?.ocr_performance || {};
  const framePump = health?.frame_pump || {};
  const powerPolicy = health?.power_policy || {};
  const performanceText = performance.report_exists
    ? [
        metricMs(performance.full_frame_ms, "完整帧"),
        metricMs(performance.roi_ms, "局部区域"),
        metricMs(performance.scaled_ms, "缩放帧"),
        metricMs(performance.cache_hit_ms, "缓存命中")
      ]
        .filter(Boolean)
        .join("，") || "已生成性能报告"
    : "未生成性能报告";

  return (
    <div>
      <PageHeader title="系统状态" description="读取 /api/v3/health、/api/v3/model/health、/api/v3/action/health，展示真实采集所需的关键就绪状态。" />
      {state.error ? (
        <Card title="接口不可用" eyebrow="/api/v3/health">
          <p className="text-sm text-red-200">{state.error}</p>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatusCard title="完整自动模式" tech="full_auto_capture_ready" ready={health?.full_auto_capture_ready} detail={blockers.length ? blockers.join(", ") : "全部关键门槛已通过"} icon="shield" />
        <StatusCard title="OCR GPU" tech="ocr_gpu_ready" ready={health?.ocr_gpu_ready} detail={labelStatus(health?.ocr_production_ready)} icon="zap" />
        <StatusCard title="ShowUI" tech="showui_ready" ready={showuiReady} detail={providerDetail(health, "showui")} icon="activity" />
        <StatusCard title="Safety Gate" tech="safety_gate_ready" ready={!blockers.includes("safety_gate_not_ready")} detail="严格模式默认启用" icon="shield" />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card title="输入与点击" eyebrow="/api/v3/action/health">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="输入网关" tech="input_gateway_ready" value={labelStatus(health?.input_gateway_ready ?? Boolean(actionHealth.input_gateway_ready))} />
            <Field label="读取鼠标位置" tech="cursor_read_ready" value={labelStatus(health?.cursor_read_ready ?? Boolean(actionHealth.cursor_read_ready))} />
            <Field label="鼠标点击" tech="mouse_click_ready" value={labelStatus(health?.mouse_click_ready ?? Boolean(actionHealth.mouse_click_ready))} />
            <Field label="交互桌面" tech="interactive_desktop_ready" value={labelStatus(health?.interactive_desktop_ready ?? Boolean(actionHealth.interactive_desktop_ready))} />
            <Field label="点击通道" tech="click_backend" value={String(health?.click_backend || actionHealth.click_backend || "-")} />
            <Field label="诊断文件" tech="input_gateway_diagnosis_path" value={health?.input_gateway_diagnosis_path || String(actionHealth.diagnosis_path || "-")} />
          </div>
        </Card>

        <Card title="OCR 单帧性能" eyebrow="/api/v3/health">
          <div className="space-y-3">
            <StatusLine label="生产门槛" value={labelStatus(health?.ocr_production_ready)} ready={health?.ocr_production_ready} />
            <StatusLine label="性能门槛" value={labelStatus(health?.ocr_performance_ready)} ready={health?.ocr_performance_ready} />
            <Field label="耗时摘要" tech="ocr_performance" value={performanceText} />
            <Field label="报告路径" tech="report_path" value={String(performance.report_path || "-")} />
          </div>
        </Card>

        <Card title="Frame Pump" eyebrow="capture worker">
          <div className="space-y-3">
            <StatusLine label="心跳状态" value={labelStatus(Boolean(framePump.ready))} ready={Boolean(framePump.ready)} />
            <Field label="状态" tech="frame_pump.status" value={String(framePump.status || "not_ready")} />
            <Field label="心跳文件" tech="heartbeat_path" value={String(framePump.heartbeat_path || "-")} />
          </div>
        </Card>

        <Card title="电源策略" eyebrow="power policy">
          <div className="space-y-3">
            <Field label="当前状态" tech="power_policy.status" value={String(powerPolicy.status || "unknown")} />
            <Field label="采集策略文件" tech="active_path" value={String(powerPolicy.active_path || "-")} />
            <Field label="恢复策略文件" tech="restored_path" value={String(powerPolicy.restored_path || "-")} />
          </div>
        </Card>
      </div>

      <Card title="阻塞项" eyebrow="blockers" className="mt-4">
        {blockers.length ? (
          <div className="flex flex-wrap gap-2">
            {blockers.map((blocker) => (
              <Badge key={blocker} className="border-amber-500/30 bg-amber-500/10 text-amber-100">
                {blocker}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-emerald-200">没有检测到阻塞项。</p>
        )}
      </Card>
    </div>
  );
}

function StatusCard({ title, tech, ready, detail, icon }: { title: string; tech: string; ready?: boolean; detail: string; icon: "shield" | "zap" | "activity" }) {
  const Icon = icon === "shield" ? ShieldCheck : icon === "zap" ? Zap : Activity;
  return (
    <Card>
      <div className="flex items-start gap-3">
        <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg border ${ready ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}>
          <Icon size={18} />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-100">{title}</p>
          <p className="text-xs text-slate-500">({tech})</p>
          <Badge className={ready ? "mt-2 border-emerald-500/30 bg-emerald-500/10 text-emerald-100" : "mt-2 border-amber-500/30 bg-amber-500/10 text-amber-100"}>{labelStatus(ready)}</Badge>
          <p className="mt-2 break-all text-xs text-slate-400">{detail}</p>
        </div>
      </div>
    </Card>
  );
}

function StatusLine({ label, value, ready }: { label: string; value: string; ready?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="inline-flex items-center gap-2 text-sm text-slate-300">{ready ? <CheckCircle2 size={15} className="text-emerald-300" /> : <AlertTriangle size={15} className="text-amber-300" />} {label}</span>
      <span className="text-sm text-slate-100">{value}</span>
    </div>
  );
}

function Field({ label, tech, value }: { label: string; tech: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <p className="text-xs text-slate-500">{label}（{tech}）</p>
      <p className="mt-1 break-all text-sm text-slate-200">{value}</p>
    </div>
  );
}

function providerDetail(health: V3Health | null, provider: string) {
  const item = health?.models?.find((model) => model.provider === provider);
  if (!item) return "未返回 provider 状态";
  return item.reason || item.status;
}

function metricMs(value: unknown, label: string) {
  return typeof value === "number" ? `${label} ${value}ms` : "";
}
