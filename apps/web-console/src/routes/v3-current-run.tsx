import { Archive, ClipboardList, FolderOpen, Images, Play, RotateCw, Square } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3CollectionSummary, V3FramePumpStatus, V3InputStatus, V3RunRecord } from "../lib/api-types";
import { isDebugRun, labelAppType, labelLanguage, labelRejectReason, labelStatus, textPolicyLabels } from "../lib/labels";

export function V3CurrentRunRoute() {
  const location = useLocation();
  const params = useParams();
  const preferredCollectionId = params.collectionId || (location.state as { collectionId?: string } | null)?.collectionId || "";
  const [collections, setCollections] = useState<V3CollectionSummary[]>([]);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [inputStatus, setInputStatus] = useState<V3InputStatus | null>(null);
  const [framePump, setFramePump] = useState<V3FramePumpStatus | null>(null);
  const [message, setMessage] = useState("正在读取当前采集项目。");
  const [showLegacyRuns, setShowLegacyRuns] = useState(false);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(false), 3000);
    return () => window.clearInterval(timer);
  }, []);

  async function load(showMessage = true) {
    try {
      const [nextCollections, nextRuns, nextInput, nextFramePump] = await Promise.all([
        apiClient.listV3Collections(),
        apiClient.listV3Runs(),
        apiClient.getV3InputStatus(),
        apiClient.getV3FramePumpStatus()
      ]);
      setCollections(nextCollections);
      setRuns(nextRuns);
      setInputStatus(nextInput);
      setFramePump(nextFramePump);
      if (showMessage) setMessage(nextCollections.length ? "已加载采集项目。继续采集会创建新轮次并自动跨轮去重。" : "暂无采集项目，请先新建任务。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  const orderedCollections = useMemo(() => {
    if (!preferredCollectionId) return collections;
    return collections
      .filter((item) => item.collection_id === preferredCollectionId)
      .concat(collections.filter((item) => item.collection_id !== preferredCollectionId));
  }, [collections, preferredCollectionId]);

  const legacyRuns = useMemo(() => runs.filter((run) => !run.collection_id && !isDebugRun(run)), [runs]);
  const debugRuns = useMemo(() => runs.filter((run) => isDebugRun(run)), [runs]);

  async function continueCollection(collectionId: string) {
    try {
      if (framePump && framePump.status !== "running") {
        const shouldStart = window.confirm("Frame Pump 未运行。当前 V3 不依赖 OBS WebSocket，采集需要 Frame Pump 持续输出截图。是否先启动 Frame Pump？");
        if (!shouldStart) return;
        await apiClient.startV3FramePump({ fps: 1, full_screen: true });
      }
      const run = await apiClient.continueV3Collection(collectionId);
      await load(false);
      setMessage(`已开始新一轮采集：第 ${run.round_index || "?"} 轮。动作预算只限制本轮自动操作次数，不代表有效截图数量。有效截图数量以去重后的累计有效图片为准。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function stopCollection(collectionId: string) {
    try {
      await apiClient.stopV3Collection(collectionId);
      await load(false);
      setMessage("采集项目已停止。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function exportCollection(collectionId: string) {
    try {
      const result = await apiClient.exportV3Collection(collectionId);
      setMessage(`最终有效截图已导出：${result.accepted_unique_total} 张，目录 ${result.export_dir}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function openInputFolder() {
    const result = await apiClient.openV3InputFolder();
    setMessage(`OBS 输出目录：${result.status} ${result.path}`);
  }

  async function startFramePump() {
    try {
      const status = await apiClient.startV3FramePump({ fps: 1, full_screen: true });
      setFramePump(status);
      await load(false);
      setMessage(status.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function stopFramePump() {
    try {
      const status = await apiClient.stopV3FramePump();
      setFramePump(status);
      await load(false);
      setMessage(status.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <div>
      <PageHeader title="当前采集项目" description="主列表按 collection 展示。继续采集会创建新轮次 run，并把本轮新增有效图计入同一个采集项目。" />

      <Card title="OBS 输入状态">
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="输出目录" value={inputStatus?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
          <Metric label="目录状态" value={inputStatus?.exists ? "存在" : "不存在"} />
          <Metric label="最近输入图片" value={inputStatus?.latest_file || "暂无"} />
          <Metric label="输入状态" value={labelStatus(inputStatus?.status)} />
        </div>
        <p className="mt-3 text-sm text-amber-200">{inputStatus?.message}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder()}>打开 OBS 输出目录</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void load()}>刷新输入状态</button>
        </div>
      </Card>

      <Card title="Frame Pump" className="mt-4">
        <div className="grid gap-3 md:grid-cols-5">
          <Metric label="状态" value={framePumpStatusText(framePump?.status)} />
          <Metric label="输出目录" value={framePump?.output_dir || inputStatus?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
          <Metric label="最近输出帧" value={framePump?.latest_frame || "暂无"} />
          <Metric label="最近输出时间" value={framePump?.latest_frame_time || "-"} />
          <Metric label="已输出帧数" value={String(framePump?.frame_count ?? 0)} />
        </div>
        <p className="mt-3 text-sm text-slate-400">
          {framePump?.message || "Frame Pump -> obs-output -> folder_watch -> OCR/去重/入库。当前链路不依赖 OBS WebSocket。"}
        </p>
        {framePump?.status === "stale" || inputStatus?.status === "stale" ? <p className="mt-2 text-sm text-amber-200">等待 Frame Pump 输出截图</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void startFramePump()}>启动 Frame Pump</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void stopFramePump()}>停止 Frame Pump</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder()}>打开输出目录</button>
        </div>
      </Card>

      <p className="my-4 whitespace-pre-line text-sm text-slate-400">{message}</p>

      <div className="grid gap-4">
        {orderedCollections.length === 0 ? <Card title="暂无采集项目"><p className="text-sm text-slate-500">请先创建 WPS、WinMerge 或游戏采集项目。</p></Card> : null}
        {orderedCollections.map((collection) => (
          <Card key={collection.collection_id} title={collection.display_name || collection.task_name || collection.app_name || "采集项目"} eyebrow="collection 采集项目">
            <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-6">
              <Metric label="软件/游戏名称" value={collection.app_name || "-"} />
              <Metric label="应用类型" value={labelAppType(collection.app_type)} />
              <Metric label="目标语言" value={labelLanguage(collection.target_language)} />
              <Metric label="采集策略" value={textPolicyLabels[collection.text_policy] || collection.text_policy} />
              <Metric label="累计去重有效截图" value={`${collection.accepted_unique_total} / ${collection.target_accepted_min} / ${collection.target_accepted_soft}`} highlight />
              <Metric label="当前状态" value={collectionStatusText(collection)} />
              <Metric label="已采集轮次" value={`${collection.run_count} 轮`} />
              <Metric label="最近一轮新增有效" value={`${collection.latest_round_new_unique} 张`} />
              <Metric label="最近一轮合格" value={`${collection.latest_round_accepted} 张`} />
              <Metric label="最近一轮跨轮重复" value={`${collection.latest_round_duplicate_across_runs} 张`} />
              <Metric label="累计跨轮重复剔除" value={`${collection.duplicate_across_runs_total} 张`} />
              <Metric label="累计动作次数" value={`${collection.action_total} 次`} />
            </div>

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <Notice title="累计数据" lines={[
                `累计处理图片数：${collection.processed_total}`,
                `累计合格图片数：${collection.accepted_total}`,
                `累计去重有效图片数：${collection.accepted_unique_total}`,
                `距离小目标还差：${collection.remaining_to_min}`,
                `距离标准目标还差：${collection.remaining_to_soft}`,
                collection.min_target_reached ? "小目标已达标，可继续冲标准目标 1000。" : "小目标未达标，需要继续采集。",
                collection.soft_target_reached ? "标准目标已达标，可继续扩充或导出最终有效截图。" : "标准目标未达标。"
              ]} />
              <Notice title="本轮数据" lines={[
                `当前轮次编号：${collection.latest_round_index || "-"}`,
                `本轮已处理：${collection.latest_round_processed}`,
                `本轮合格：${collection.latest_round_accepted}`,
                `本轮新增有效：${collection.latest_round_new_unique}`,
                `本轮跨轮重复：${collection.latest_round_duplicate_across_runs}`,
                `本轮拒绝：${collection.latest_round_rejected}`,
                `本轮失败：${collection.latest_round_failed}`,
                `本轮主要拒绝原因：${collection.latest_round_top_reject_reasons.map((item) => `${labelRejectReason(item.reason)} ${item.count}`).join("，") || "-"}`
              ]} />
            </div>

            {collection.continue_suggestion ? <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">{collection.continue_suggestion}</p> : null}

            <p className="mt-3 text-xs text-slate-500">
              动作预算只限制本轮自动操作次数，不代表有效截图数量。有效截图数量以去重后的累计有效图片为准。如果本轮未达标，可以继续采集，系统会自动跨轮去重并累计。
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <ActionButton icon={<Play size={15} />} label="继续采集" onClick={() => void continueCollection(collection.collection_id)} />
              <ActionButton icon={<Square size={15} />} label="停止项目" onClick={() => void stopCollection(collection.collection_id)} />
              <LinkButton icon={<Images size={15} />} label="查看累计图库" to={`/v3/collections/${collection.collection_id}/gallery`} />
              <LinkButton icon={<ClipboardList size={15} />} label="查看所有轮次" to={`/v3/collections/${collection.collection_id}/runs`} />
              <ActionButton icon={<Archive size={15} />} label="导出最终有效图" onClick={() => void exportCollection(collection.collection_id)} />
              <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => setMessage(`最终有效图库：${collection.accepted_unique_dir || "-"}`)}>
                <FolderOpen size={15} />打开文件夹
              </button>
            </div>

            <details className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
              <summary className="cursor-pointer text-sm text-slate-300">所有轮次 / 高级调试</summary>
              <div className="mt-3 grid gap-2">
                {collection.runs.map((run) => (
                  <div key={String(run.run_id)} className="grid gap-2 rounded border border-slate-800 p-2 text-xs text-slate-400 md:grid-cols-6">
                    <span>第 {String(run.round_index)} 轮</span>
                    <span>run_id：{String(run.run_id)}</span>
                    <span>状态：{labelStatus(String(run.status))}</span>
                    <span>合格：{String(run.accepted)}</span>
                    <span>新增有效：{String(run.new_unique)}</span>
                    <span>跨轮重复：{String(run.duplicate_across_runs)}</span>
                  </div>
                ))}
              </div>
            </details>
          </Card>
        ))}
      </div>

      <details className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
        <summary className="cursor-pointer text-sm text-slate-300" onClick={() => setShowLegacyRuns(!showLegacyRuns)}>历史未归类任务 / 调试样本（默认隐藏）</summary>
        {showLegacyRuns ? (
          <div className="mt-3 grid gap-2 text-xs text-slate-500">
            {legacyRuns.concat(debugRuns).map((run) => <div key={run.run_id}>run_id：{run.run_id}，状态：{labelStatus(run.status)}</div>)}
          </div>
        ) : null}
      </details>
    </div>
  );
}

function collectionStatusText(collection: V3CollectionSummary) {
  if (collection.max_target_reached) return "达到最大扩充目标，建议停止";
  if (collection.soft_target_reached) return "标准目标达标";
  if (collection.min_target_reached) return "小目标达标，可冲标准目标";
  if (collection.status === "collecting") return "采集中";
  if (collection.accepted_unique_total > 0) return "数量不足，需要继续采集";
  return "未开始或无有效结果";
}

function framePumpStatusText(status?: V3FramePumpStatus["status"]) {
  if (status === "running") return "运行中";
  if (status === "stale" || status === "error") return "异常";
  return "未运行";
}

function Metric({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 ${highlight ? "border-emerald-500/40 bg-emerald-500/10" : "border-slate-800 bg-slate-950"}`}>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 break-all text-base font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function Notice({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      <div className="mt-2 grid gap-1 text-sm text-slate-400">
        {lines.map((line) => <span key={line}>{line}</span>)}
      </div>
    </div>
  );
}

function ActionButton({ icon, label, onClick }: { icon: ReactNode; label: string; onClick: () => void }) {
  return <button className="inline-flex items-center gap-2 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={onClick}>{icon}{label}</button>;
}

function LinkButton({ icon, label, to }: { icon: ReactNode; label: string; to: string }) {
  return <Link className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={to}>{icon}{label}</Link>;
}
