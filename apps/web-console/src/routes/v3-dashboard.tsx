import { FolderOpen, Gamepad2, ListPlus, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3Health, V3RunRecord, V3Summary } from "../lib/api-types";
import { labelStatus } from "../lib/labels";

export function V3DashboardRoute() {
  const [health, setHealth] = useState<V3Health | null>(null);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [summary, setSummary] = useState<V3Summary | null>(null);
  const [message, setMessage] = useState("前端已连接 V3 单机采集接口。");

  async function load() {
    const [nextHealth, nextRuns] = await Promise.all([apiClient.getV3Health(), apiClient.listV3Runs()]);
    setHealth(nextHealth);
    setRuns(nextRuns);
    const latest = nextRuns[0];
    setSummary(latest ? await apiClient.getV3Summary(latest.run_id) : null);
  }

  useEffect(() => {
    void load();
  }, []);

  const latestRun = runs[0];
  const recentRuns = useMemo(() => runs.slice(0, 5), [runs]);

  async function openLatestRunFolder() {
    if (!latestRun) {
      setMessage("暂无 run 可打开。");
      return;
    }
    const result = await apiClient.openV3RunFolder(latestRun.run_id);
    setMessage(`打开最近 run：${result.status} ${result.path}`);
  }

  async function openStaticFolder(path: string) {
    await navigator.clipboard?.writeText(path);
    setMessage(`已复制本地路径：${path}`);
  }

  return (
    <div>
      <PageHeader title="V3 控制台" description="面向操作员的单机采集台：看状态、开任务、看结果、查路径。" />

      <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <Card title="当前系统状态" eyebrow="readiness">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Metric label="完整自动采集就绪" tech="full_auto_capture_ready" value={labelStatus(health?.full_auto_capture_ready)} />
            <Metric label="OCR GPU 就绪" tech="ocr_gpu_ready" value={labelStatus(health?.ocr_gpu_ready)} />
            <Metric label="ShowUI 就绪" tech="showui_ready" value={labelStatus(health?.models?.some((item) => item.provider === "showui" && item.status === "ready"))} />
            <Metric label="输入网关就绪" tech="input_gateway_ready" value={labelStatus(health?.input_gateway_ready)} />
            <Metric label="Safety Gate 就绪" tech="safety_gate_ready" value={labelStatus(health?.readiness_blockers?.length === 0)} />
            <Metric label="Frame Pump 状态" tech="frame_pump" value="按任务脚本运行" />
          </div>
          {(health?.readiness_blockers?.length || health?.input_gateway_blockers?.length) ? (
            <p className="mt-3 break-all font-mono text-xs text-amber-300">
              阻塞项：{[...(health?.readiness_blockers || []), ...(health?.input_gateway_blockers || [])].join(", ")}
            </p>
          ) : null}
        </Card>

        <Card title="当前运行任务" eyebrow={latestRun?.run_id || "暂无任务"}>
          {latestRun ? (
            <div className="grid gap-3">
              <Metric label="软件/游戏名称" tech="app_name" value={latestRun.config.app_name} />
              <div className="grid gap-3 sm:grid-cols-2">
                <Metric label="目标语言" tech="target_language" value={latestRun.config.target_language} />
                <Metric label="类型" tech="app_type" value={latestRun.config.app_type} />
                <Metric label="processed" value={String(summary?.processed ?? 0)} />
                <Metric label="accepted" value={String(summary?.accepted ?? latestRun.counts.accepted ?? 0)} />
                <Metric label="rejected" value={String(summary?.rejected ?? latestRun.counts.rejected ?? 0)} />
                <Metric label="failed" value={String(summary?.failed ?? 0)} />
                <Metric label="quarantined" value={String(summary?.quarantined ?? 0)} />
                <Metric label="action_count" value={String(latestRun.counts.actions ?? 0)} />
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">暂无运行任务。</p>
          )}
        </Card>
      </div>

      <Card title="快捷按钮" eyebrow="operator actions" className="mt-4">
        <div className="flex flex-wrap gap-2">
          <ActionLink to="/v3/new" icon={<ListPlus size={16} />} label="新建软件采集" />
          <ActionLink to="/v3/game" icon={<Gamepad2 size={16} />} label="新建游戏采集" />
          <ActionLink to={latestRun ? `/v3/runs/${latestRun.run_id}/gallery` : "/v3/gallery"} icon={<FolderOpen size={16} />} label="打开最近 run" />
          <ActionButton label="打开 runs 文件夹" onClick={() => void openStaticFolder("D:\\work\\app-shot\\runs\\v3")} />
          <ActionButton label="打开 obs-output 文件夹" onClick={() => void openStaticFolder("D:\\work\\app-shot\\obs-output")} />
          <ActionButton label="运行自检" icon={<RefreshCw size={16} />} onClick={() => setMessage("请运行 scripts/v3/diagnose/v3_self_check_app_shot.ps1，报告在 D:\\work\\app-shot\\reports。")} />
          <ActionButton label="打开最近 run 文件夹" onClick={() => void openLatestRunFolder()} />
        </div>
        <p className="mt-3 text-sm text-slate-400">{message}</p>
      </Card>

      <Card title="最近 5 个 run" eyebrow="runs" className="mt-4">
        <div className="grid gap-2">
          {recentRuns.length === 0 ? <p className="text-sm text-slate-500">暂无 V3 run。</p> : null}
          {recentRuns.map((run) => {
            const accepted = run.counts.accepted || 0;
            const rejected = run.counts.rejected || 0;
            const passed = accepted >= 50 && (run.counts.actions || 0) <= 30;
            return (
              <div key={run.run_id} className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950 p-3 md:grid-cols-[1.4fr_0.8fr_0.55fr_0.8fr_0.5fr_0.7fr]">
                <span className="break-all font-mono text-xs text-blue-200">{run.run_id}</span>
                <span className="text-sm text-slate-300">{run.config.app_name}</span>
                <span className="text-sm text-slate-400">{run.config.app_type}</span>
                <span className="text-sm text-slate-400">合格 {accepted} / 拒绝 {rejected}</span>
                <span className={passed ? "text-sm text-emerald-300" : "text-sm text-amber-300"}>{passed ? "通过" : "观察"}</span>
                <Link className="text-sm text-blue-300 hover:text-blue-200" to={`/v3/runs/${run.run_id}/gallery`}>
                  查看结果
                </Link>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value, tech }: { label: string; value: string; tech?: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{tech ? `${label}（${tech}）` : label}</p>
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

function ActionButton({ label, onClick, icon }: { label: string; onClick: () => void; icon?: ReactNode }) {
  return (
    <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800" onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}
