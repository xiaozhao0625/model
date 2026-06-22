import { FolderOpen, Gamepad2, ListPlus, MonitorDot, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3Health, V3InputStatus, V3RunRecord, V3Summary } from "../lib/api-types";
import { displayRunName, isDebugRun, labelAppType, labelStatus } from "../lib/labels";

export function V3DashboardRoute() {
  const [health, setHealth] = useState<V3Health | null>(null);
  const [inputStatus, setInputStatus] = useState<V3InputStatus | null>(null);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [summary, setSummary] = useState<V3Summary | null>(null);
  const [message, setMessage] = useState("正在连接本机 V3 采集服务。");

  async function load() {
    try {
      const [nextHealth, nextRuns, nextInput] = await Promise.all([apiClient.getV3Health(), apiClient.listV3Runs(), apiClient.getV3InputStatus()]);
      const visible = nextRuns.filter((run) => !isDebugRun(run));
      setHealth(nextHealth);
      setRuns(visible);
      setInputStatus(nextInput);
      setSummary(visible[0] ? await apiClient.getV3Summary(visible[0].run_id) : null);
      setMessage("本机 V3 采集服务正常。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const latestRun = runs[0];
  const recentRuns = useMemo(() => runs.slice(0, 5), [runs]);

  return (
    <div>
      <PageHeader title="V3 操作员采集控制台" description="从这里创建任务、开始采集、等待 OBS 输入、查看处理进度和结果图库。" />

      <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <Card title="系统就绪状态">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Metric label="后端 API" value={health ? "正常" : "异常"} />
            <Metric label="OBS 输入目录" value={labelStatus(inputStatus?.status)} />
            <Metric label="PaddleOCR" value={labelStatus(health?.ocr?.some((item) => item.provider === "paddleocr" && item.status === "ready"))} />
            <Metric label="OCR GPU" value={labelStatus(health?.ocr_gpu_ready)} />
            <Metric label="ShowUI" value={labelStatus(health?.models?.some((item) => item.provider === "showui" && item.status === "ready" && item.enabled))} />
            <Metric label="Input Gateway" value={labelStatus(health?.input_gateway_ready)} />
          </div>
          <p className="mt-3 text-sm text-slate-400">V3 单机模式不需要 Redis、PostgreSQL 或 Docker。</p>
        </Card>

        <Card title="最近任务">
          {latestRun ? (
            <div className="grid gap-3">
              <Metric label="任务名称" value={displayRunName(latestRun)} />
              <Metric label="软件/游戏" value={latestRun.config.app_name} />
              <Metric label="类型" value={labelAppType(latestRun.config.app_type)} />
              <Metric label="状态" value={labelStatus(summary?.status || latestRun.status)} />
              <Metric label="目标进度" value={`已合格 ${summary?.accepted ?? latestRun.counts.accepted ?? 0} / ${summary?.target_accepted_min || latestRun.config.target_accepted_min || 800}`} />
            </div>
          ) : (
            <p className="text-sm text-slate-500">暂无真实采集任务。</p>
          )}
        </Card>
      </div>

      <Card title="操作入口" className="mt-4">
        <div className="flex flex-wrap gap-2">
          <ActionLink to="/v3/new" icon={<ListPlus size={16} />} label="新建采集任务" />
          <ActionLink to="/v3/game" icon={<Gamepad2 size={16} />} label="新建游戏采集" />
          <ActionLink to="/v3/current" icon={<MonitorDot size={16} />} label="当前任务与采集控制" />
          <ActionLink to={latestRun ? `/v3/runs/${latestRun.run_id}/gallery` : "/v3/gallery"} icon={<FolderOpen size={16} />} label="查看结果图库" />
          <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void load()}>
            <RefreshCw size={16} />刷新状态
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-400">{message}</p>
      </Card>

      <Card title="最近真实任务" className="mt-4">
        <div className="grid gap-2">
          {recentRuns.length === 0 ? <p className="text-sm text-slate-500">暂无任务，请先新建。</p> : null}
          {recentRuns.map((run) => (
            <Link key={run.run_id} to="/v3/current" state={{ runId: run.run_id }} className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950 p-3 md:grid-cols-[1.2fr_1fr_0.8fr_0.8fr]">
              <span className="text-sm font-medium text-slate-100">{displayRunName(run)}</span>
              <span className="text-sm text-slate-300">{run.config.app_name}</span>
              <span className="text-sm text-slate-400">{labelAppType(run.config.app_type)}</span>
              <span className="text-sm text-slate-400">合格 {run.counts.accepted || 0} / 已拒绝 {run.counts.rejected || 0}</span>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function ActionLink({ to, icon, label }: { to: string; icon: ReactNode; label: string }) {
  return (
    <Link to={to} className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100 hover:bg-blue-500/10">
      {icon}
      {label}
    </Link>
  );
}
