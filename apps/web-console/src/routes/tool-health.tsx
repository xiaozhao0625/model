import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3Health, V3InputStatus, V3RunRecord } from "../lib/api-types";
import { isDebugRun, labelStatus } from "../lib/labels";

type State = {
  health: V3Health | null;
  input: V3InputStatus | null;
  runs: V3RunRecord[];
  error: string | null;
};

export function ToolHealthRoute() {
  const [state, setState] = useState<State>({ health: null, input: null, runs: [], error: null });

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [health, input, runs] = await Promise.all([apiClient.getV3Health(), apiClient.getV3InputStatus(), apiClient.listV3Runs()]);
      setState({ health, input, runs: runs.filter((run) => !isDebugRun(run)), error: null });
    } catch (error) {
      setState({ health: null, input: null, runs: [], error: error instanceof Error ? error.message : String(error) });
    }
  }

  const health = state.health;
  const runningCount = useMemo(() => state.runs.filter((run) => ["running", "waiting_for_input"].includes(run.status)).length, [state.runs]);
  const recentErrors = useMemo(() => state.runs.map((run) => run.last_error).filter(Boolean).slice(0, 5), [state.runs]);
  const paddle = health?.ocr?.find((item) => item.provider === "paddleocr");
  const showui = health?.models?.find((item) => item.provider === "showui");

  return (
    <div>
      <PageHeader title="系统状态" description="检查本机 V3 采集所需组件。V3 单机模式不需要 Redis、PostgreSQL 或 Docker。" />
      {state.error ? <Card title="接口异常"><p className="text-sm text-red-200">{state.error}</p></Card> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatusCard label="后端 API" value={health ? "正常" : "异常"} ok={Boolean(health)} />
        <StatusCard label="前端" value="正常" ok />
        <StatusCard label="OBS 输入目录" value={labelStatus(state.input?.status)} ok={state.input?.status === "receiving" || state.input?.status === "waiting_for_input" || state.input?.status === "stale"} />
        <StatusCard label="PaddleOCR" value={paddle?.status === "ready" ? "正常" : "异常"} ok={paddle?.status === "ready"} />
        <StatusCard label="OCR GPU" value={labelStatus(health?.ocr_gpu_ready)} ok={health?.ocr_gpu_ready} />
        <StatusCard label="ShowUI" value={showui?.status === "ready" && showui.enabled ? "正常" : "异常"} ok={showui?.status === "ready" && showui.enabled} />
        <StatusCard label="Input Gateway" value={labelStatus(health?.input_gateway_ready)} ok={health?.input_gateway_ready} />
        <StatusCard label="FFmpeg" value="已检测" ok />
        <StatusCard label="OBS" value="已检测" ok={state.input?.exists} />
        <StatusCard label="防息屏" value={String(health?.power_policy?.status || "未知")} ok={health?.power_policy?.status === "active" || health?.power_policy?.status === "unknown"} />
        <StatusCard label="当前运行任务数" value={String(runningCount)} ok />
        <StatusCard label="完整自动采集" value={labelStatus(health?.full_auto_capture_ready)} ok={health?.full_auto_capture_ready} />
      </div>

      <Card title="OBS 输入详情" className="mt-4">
        <div className="grid gap-3 md:grid-cols-4">
          <Field label="输出目录" value={state.input?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
          <Field label="最近输入图片" value={state.input?.latest_file || "暂无"} />
          <Field label="最近输入时间" value={state.input?.latest_file_time || "-"} />
          <Field label="距离当前" value={state.input?.seconds_since_latest === undefined || state.input?.seconds_since_latest === null ? "-" : `${state.input.seconds_since_latest} 秒`} />
        </div>
        <p className="mt-3 text-sm text-slate-400">{state.input?.message}</p>
      </Card>

      <Card title="最近错误" className="mt-4">
        {recentErrors.length ? recentErrors.map((item) => <p key={String(item)} className="text-sm text-amber-200">{String(item)}</p>) : <p className="text-sm text-emerald-200">暂无最近错误。</p>}
      </Card>

      <button className="mt-4 inline-flex items-center gap-2 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void load()}>
        <RefreshCw size={16} />刷新状态
      </button>
    </div>
  );
}

function StatusCard({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <Card>
      <p className="text-sm font-semibold text-slate-100">{label}</p>
      <p className={ok ? "mt-2 text-lg font-semibold text-emerald-200" : "mt-2 text-lg font-semibold text-amber-200"}>{value}</p>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 break-all text-sm text-slate-200">{value}</p></div>;
}
