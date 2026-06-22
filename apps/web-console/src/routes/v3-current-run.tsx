import { FolderOpen, Pause, Play, RotateCw, Square, Images, ClipboardList } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3InputStatus, V3RunRecord, V3Summary } from "../lib/api-types";
import { displayRunName, isDebugRun, labelAppType, labelLanguage, labelRejectReason, labelStatus } from "../lib/labels";

export function V3CurrentRunRoute() {
  const location = useLocation();
  const preferredRunId = (location.state as { runId?: string } | null)?.runId || "";
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [summaries, setSummaries] = useState<Record<string, V3Summary>>({});
  const [inputStatus, setInputStatus] = useState<V3InputStatus | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [message, setMessage] = useState("正在读取当前任务。");

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(false), 3000);
    return () => window.clearInterval(timer);
  }, []);

  async function load(showMessage = true) {
    try {
      const [nextRuns, nextInput] = await Promise.all([apiClient.listV3Runs(), apiClient.getV3InputStatus()]);
      const sorted = [...nextRuns].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
      setRuns(sorted);
      setInputStatus(nextInput);
      const visible = sorted.filter((run) => !isDebugRun(run));
      const selectedRuns = preferredRunId
        ? sorted.filter((run) => run.run_id === preferredRunId).concat(visible.filter((run) => run.run_id !== preferredRunId))
        : visible;
      const entries = await Promise.all(selectedRuns.slice(0, 8).map(async (run) => [run.run_id, await apiClient.getV3Summary(run.run_id)] as const));
      setSummaries(Object.fromEntries(entries));
      if (showMessage) setMessage(selectedRuns.length ? "已加载最近真实任务。" : "暂无真实任务，请先新建采集任务。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  const visibleRuns = useMemo(() => runs.filter((run) => !isDebugRun(run)), [runs]);
  const debugRuns = useMemo(() => runs.filter((run) => isDebugRun(run)), [runs]);
  const orderedRuns = preferredRunId
    ? runs.filter((run) => run.run_id === preferredRunId).concat(visibleRuns.filter((run) => run.run_id !== preferredRunId))
    : visibleRuns;

  async function runAction(runId: string, action: "start" | "pause" | "resume" | "stop") {
    try {
      if (action === "start") await apiClient.startV3Run(runId);
      if (action === "pause") await apiClient.pauseV3Run(runId);
      if (action === "resume") await apiClient.resumeV3Run(runId);
      if (action === "stop") await apiClient.stopV3Run(runId);
      await load(false);
      setMessage(actionLabel(action) + "已执行。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function openInputFolder() {
    const result = await apiClient.openV3InputFolder();
    setMessage(`OBS 输出目录：${result.status} ${result.path}`);
  }

  return (
    <div>
      <PageHeader title="当前任务" description="创建任务后在这里开始采集、等待 OBS 输入、查看处理进度和打开结果。" />

      <Card title="OBS 输入状态">
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="输出目录" value={inputStatus?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
          <Metric label="目录状态" value={inputStatus?.exists ? "存在" : "不存在"} />
          <Metric label="最近输入图片" value={inputStatus?.latest_file || "暂无"} />
          <Metric label="输入状态" value={labelStatus(inputStatus?.status)} />
          <Metric label="最近输入时间" value={inputStatus?.latest_file_time || "-"} />
          <Metric label="距今秒数" value={inputStatus?.seconds_since_latest === undefined || inputStatus?.seconds_since_latest === null ? "-" : `${inputStatus.seconds_since_latest} 秒`} />
        </div>
        <p className="mt-3 text-sm text-amber-200">{inputStatus?.message}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder()}>打开 OBS 输出目录</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void load()}>刷新输入状态</button>
        </div>
      </Card>

      <p className="my-4 whitespace-pre-line text-sm text-slate-400">{message}</p>

      <div className="grid gap-4">
        {orderedRuns.length === 0 ? <Card title="暂无真实任务"><p className="text-sm text-slate-500">请先创建软件或游戏采集任务。</p></Card> : null}
        {orderedRuns.slice(0, 8).map((run) => {
          const summary = summaries[run.run_id];
          const status = summary?.status || run.status;
          const target = summary?.target_accepted_min || run.config.target_accepted_min || 800;
          const accepted = summary?.accepted ?? run.counts.accepted ?? 0;
          const topReason = summary?.top_reject_reason || Object.entries(summary?.reject_reason_distribution || {}).sort((a, b) => b[1] - a[1])[0]?.[0];
          return (
            <Card key={run.run_id} title={displayRunName(run)} eyebrow={`任务编号：${run.run_id}`}>
              <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-6">
                <Metric label="软件/游戏名称" value={run.config.app_name} />
                <Metric label="类型" value={labelAppType(run.config.app_type)} />
                <Metric label="状态" value={labelStatus(status)} />
                <Metric label="目标语言" value={labelLanguage(run.config.target_language)} />
                <Metric label="目标进度" value={`已合格 ${accepted} / ${target}`} />
                <Metric label="已处理" value={String(summary?.processed ?? 0)} />
                <Metric label="合格" value={String(accepted)} />
                <Metric label="已拒绝" value={String(summary?.rejected ?? run.counts.rejected ?? 0)} />
                <Metric label="失败" value={String(summary?.failed ?? 0)} />
                <Metric label="动作次数" value={String(run.counts.actions ?? 0)} />
                <Metric label="最近输入时间" value={summary?.latest_input_at || "-"} />
                <Metric label="最近合格时间" value={summary?.latest_accepted_at || "-"} />
                <Metric label="最多拒绝原因" value={labelRejectReason(topReason)} />
                <Metric label="OBS 状态" value={labelStatus(summary?.input_status?.status || inputStatus?.status)} />
                {run.config.app_type === "pc_game" ? (
                  <>
                    <Metric label="文字图数量" value={String(summary?.accepted_text_ui_count ?? 0)} />
                    <Metric label="HUD 文字图数量" value={String(summary?.accepted_text_hud_count ?? 0)} />
                    <Metric label="无文字补充图" value={String(summary?.accepted_visual_fill_count ?? 0)} />
                    <Metric label="补充图占比" value={`${Math.round((summary?.no_text_fill_ratio_actual || 0) * 100)}%`} />
                  </>
                ) : null}
              </div>

              {status === "waiting_for_input" ? (
                <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                  正在等待 OBS 输出截图，请确认 OBS 已启动，并且输出目录为 D:\work\app-shot\obs-output。
                </p>
              ) : null}

              <div className="mt-4 flex flex-wrap gap-2">
                <ActionButton icon={<Play size={15} />} label="开始采集" onClick={() => void runAction(run.run_id, "start")} />
                <ActionButton icon={<Pause size={15} />} label="暂停" onClick={() => void runAction(run.run_id, "pause")} />
                <ActionButton icon={<RotateCw size={15} />} label="继续" onClick={() => void runAction(run.run_id, "resume")} />
                <ActionButton icon={<Square size={15} />} label="停止" onClick={() => void runAction(run.run_id, "stop")} />
                <LinkButton icon={<Images size={15} />} label="查看图库" to={`/v3/runs/${run.run_id}/gallery`} />
                <LinkButton icon={<ClipboardList size={15} />} label="查看详情 / 审计" to={`/v3/runs/${run.run_id}/actions`} />
                <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void apiClient.openV3RunFolder(run.run_id).then((result) => setMessage(`本地结果文件夹：${result.status} ${result.path}`))}>
                  <FolderOpen size={15} />打开本地文件夹
                </button>
              </div>
            </Card>
          );
        })}
      </div>

      <details className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
        <summary className="cursor-pointer text-sm text-slate-300" onClick={() => setShowDebug(!showDebug)}>历史测试任务 / 调试样本（默认隐藏）</summary>
        {showDebug ? (
          <div className="mt-3 grid gap-2">
            {debugRuns.map((run) => (
              <div key={run.run_id} className="rounded border border-slate-800 p-2 text-xs text-slate-500">
                {displayRunName(run)} - 任务编号：{run.run_id}
              </div>
            ))}
          </div>
        ) : null}
      </details>
    </div>
  );
}

function actionLabel(action: string) {
  return { start: "开始采集", pause: "暂停", resume: "继续", stop: "停止" }[action] || action;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 break-all text-base font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function ActionButton({ icon, label, onClick }: { icon: ReactNode; label: string; onClick: () => void }) {
  return <button className="inline-flex items-center gap-2 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={onClick}>{icon}{label}</button>;
}

function LinkButton({ icon, label, to }: { icon: ReactNode; label: string; to: string }) {
  return <Link className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={to}>{icon}{label}</Link>;
}
