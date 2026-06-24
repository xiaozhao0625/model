import { Archive, ClipboardList, FolderOpen, Images, Play, RotateCw, Square, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { ObsFramePumpPanel } from "../components/v3/obs-frame-pump-panel";
import { apiClient } from "../lib/api-client";
import type { V3ActionHealth, V3AgentConfigRequest, V3CollectionSummary, V3FramePumpStatus, V3InputStatus, V3RunRecord, V3TargetWindowInfo } from "../lib/api-types";
import { isDebugRun, labelAppType, labelLanguage, labelRejectReason, labelStatus, textPolicyLabels } from "../lib/labels";

export function V3CurrentRunRoute() {
  const location = useLocation();
  const params = useParams();
  const preferredCollectionId = params.collectionId || (location.state as { collectionId?: string } | null)?.collectionId || "";
  const [collections, setCollections] = useState<V3CollectionSummary[]>([]);
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [inputStatus, setInputStatus] = useState<V3InputStatus | null>(null);
  const [framePump, setFramePump] = useState<V3FramePumpStatus | null>(null);
  const [actionHealth, setActionHealth] = useState<V3ActionHealth | null>(null);
  const [windows, setWindows] = useState<V3TargetWindowInfo[]>([]);
  const [message, setMessage] = useState("正在读取当前采集项目。");
  const [showLegacyRuns, setShowLegacyRuns] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<{ collectionId: string; text: string } | null>(null);

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (busyAction) return;
    const timer = window.setInterval(() => void load(false), 3000);
    return () => window.clearInterval(timer);
  }, [busyAction]);

  async function load(showMessage = true) {
    try {
      const [nextCollections, nextRuns, nextInput, nextFramePump] = await Promise.all([
        apiClient.listV3Collections(),
        apiClient.listV3Runs(),
        apiClient.getV3InputStatus(),
        apiClient.getV3FramePumpStatus()
      ]);
      const visibleCollections = nextCollections.filter((collection) => !isDebugCollection(collection));
      const selectedCollection = preferredCollectionId
        ? visibleCollections.find((item) => item.collection_id === preferredCollectionId) || visibleCollections[0]
        : visibleCollections[0];
      const nextActionHealth = selectedCollection ? await apiClient.getV3ActionHealth(selectedCollection.collection_id) : await apiClient.getV3ActionHealth();
      setCollections(visibleCollections);
      setRuns(nextRuns);
      setInputStatus(nextInput);
      setFramePump(nextFramePump);
      setActionHealth(nextActionHealth);
      if (showMessage) setMessage(visibleCollections.length ? "已加载采集项目。继续采集会创建新轮次并自动跨轮去重。" : "暂无采集项目，请先新建任务。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  const orderedCollections = useMemo(() => {
    if (!preferredCollectionId) return collections;
    return collections
      .filter((item) => item.collection_id === preferredCollectionId)
      .concat(collections.filter((item) => item.collection_id !== preferredCollectionId));
  }, [collections, preferredCollectionId]);
  const primaryCollection = orderedCollections[0];

  const legacyRuns = useMemo(() => runs.filter((run) => !run.collection_id && !isDebugRun(run)), [runs]);
  const debugRuns = useMemo(() => runs.filter((run) => isDebugRun(run)), [runs]);

  function replaceCollection(next: V3CollectionSummary) {
    setCollections((current) => current.map((item) => (item.collection_id === next.collection_id ? next : item)));
  }

  async function updateAgentConfig(collection: V3CollectionSummary, patch: V3AgentConfigRequest = {}, showSaved = true) {
    if (busyAction) return collection;
    setBusyAction(`agent:${collection.collection_id}`);
    try {
      const updated = await apiClient.updateV3CollectionAgentConfig(collection.collection_id, buildAgentConfigPayload(collection, patch));
      replaceCollection(updated);
      if (showSaved) setMessage("AI 自动探索配置已保存到 collection，后续轮次会继承。");
      return updated;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
      return collection;
    } finally {
      setBusyAction(null);
    }
  }

  async function enableAgentAndContinue(collection: V3CollectionSummary) {
    if (!window.confirm("请确认已经手动进入训练场、靶场、单机、局外背包/仓库/地图等安全场景；系统不会自动登录、充值、匹配、排位或聊天。")) return;
    setBusyAction(`agent-continue:${collection.collection_id}`);
    try {
      const updated = await apiClient.updateV3CollectionAgentConfig(collection.collection_id, buildAgentConfigPayload(collection, {
        enable_game_agent: true,
        enable_game_explorer: true,
        game_agent_mode: "auto_explore",
        allow_ui_click: true,
        allow_hotkeys: true,
        allow_wasd: true,
        allow_mouse_look: true,
        allow_back_close: true,
        allow_inventory_map_explore: true,
        allow_training_movement: true,
        allow_wasd_mouse: true,
        safe_scene_confirmed: true,
        safe_game_scene_confirmed: true
      }));
      replaceCollection(updated);
      setBusyAction(null);
      await continueCollection(updated.collection_id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
      setBusyAction(null);
    }
  }

  async function continueCollection(collectionId: string) {
    if (busyAction) return;
    setBusyAction(`continue:${collectionId}`);
    try {
      const collection = collections.find((item) => item.collection_id === collectionId);
      const synced = collection ? await apiClient.updateV3CollectionAgentConfig(collection.collection_id, buildAgentConfigPayload(collection)) : null;
      if (synced) replaceCollection(synced);
      const effectiveCollection = synced || collection;
      const outputDir = effectiveCollection?.watch_dir || effectiveCollection?.input_dir || effectiveCollection?.frame_pump_output_dir || undefined;
      if (framePump && framePump.status !== "running") {
        const shouldStart = window.confirm("Frame Pump 未运行。当前 V3 不依赖 OBS WebSocket，采集需要 Frame Pump 持续输出截图。是否先启动 Frame Pump？");
        if (!shouldStart) return;
        await apiClient.startV3FramePump({ fps: 1, full_screen: true, source_mode: "screen", output_dir: outputDir });
      }
      if (effectiveCollection && (effectiveCollection.enable_game_agent || effectiveCollection.enable_game_explorer) && effectiveCollection.real_input_enabled) {
        setMessage("3 秒后切换到目标游戏窗口并开始自动探索，请不要操作鼠标键盘。");
        await delay(3000);
        const focus = await apiClient.focusV3TargetWindow(effectiveCollection.collection_id);
        if (!focus.ok) {
          setMessage(`目标窗口切换失败：${focus.blocked_reason || "target_window_not_foreground"}。请先选择目标窗口或手动切回游戏窗口。`);
        }
      }
      const run = await apiClient.continueV3Collection(collectionId);
      await load(false);
      setMessage(`已开始新一轮采集：第 ${run.round_index || "?"} 轮。动作预算只限制本轮自动操作次数，不代表有效截图数量。有效截图数量以去重后的累计有效图片为准。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function stopCollection(collection: V3CollectionSummary) {
    if (busyAction) return;
    if (collection.status === "stopped") {
      setMessage("采集项目已经停止。");
      return;
    }
    setBusyAction(`stop:${collection.collection_id}`);
    try {
      await apiClient.stopV3Collection(collection.collection_id);
      await load(false);
      setMessage("采集项目已停止。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function exportCollection(collection: V3CollectionSummary) {
    if (busyAction) return;
    setBusyAction(`export:${collection.collection_id}`);
    setExportResult(null);
    if (collection.accepted_unique_total <= 0) {
      const text = "当前没有最终有效图，无法导出。请先完成采集或查看被拒绝原因。";
      setMessage(text);
      setExportResult({ collectionId: collection.collection_id, text });
      setBusyAction(null);
      return;
    }
    try {
      setMessage("正在导出最终有效图...");
      const result = await apiClient.exportV3Collection(collection.collection_id);
      const text = [
        result.message || "导出成功",
        `最终有效图数量：${result.accepted_unique_total}`,
        `导出目录：${result.export_dir}`,
        `zip 包：${result.zip_path || result.archive_path || "-"}`,
        `manifest：${result.manifest_path}`,
        `summary：${result.summary_path}`
      ].join("\n");
      setExportResult({ collectionId: collection.collection_id, text });
      setMessage(text);
    } catch (error) {
      const text = error instanceof Error ? error.message : String(error);
      setExportResult({ collectionId: collection.collection_id, text });
      setMessage(text);
    } finally {
      setBusyAction(null);
    }
  }

  async function deleteCollection(collection: V3CollectionSummary) {
    if (busyAction) return;
    const name = collection.display_name || collection.task_name || collection.app_name || collection.collection_id;
    if (!window.confirm(`确认删除采集项目“${name}”？默认只软删除，可在后续恢复。`)) return;
    const deleteFiles = window.confirm("是否同时把项目文件移入 runs/v3/trash？\n选择“取消”会执行软删除。");
    if (deleteFiles && !window.confirm("二次确认：文件会被移入 trash，不会永久删除。是否继续？")) return;
    setBusyAction(`delete:${collection.collection_id}`);
    try {
      const result = await apiClient.deleteV3Collection(collection.collection_id, deleteFiles);
      await load(false);
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function deleteRun(runId: string) {
    if (busyAction) return;
    if (!window.confirm(`确认删除轮次 ${runId}？默认软删除并重新计算 collection 汇总。`)) return;
    const deleteFiles = window.confirm("是否同时把该轮次文件移入 runs/v3/trash？\n选择“取消”会执行软删除。");
    if (deleteFiles && !window.confirm("二次确认：轮次文件会被移入 trash，不会永久删除。是否继续？")) return;
    setBusyAction(`delete-run:${runId}`);
    try {
      const result = await apiClient.deleteV3Run(runId, deleteFiles);
      await load(false);
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function openInputFolder(collectionId?: string) {
    const result = await apiClient.openV3InputFolder(collectionId);
    setMessage(`OBS 输出目录：${result.status} ${result.path}`);
  }

  async function openExportFolder(collectionId: string) {
    const result = await apiClient.openV3CollectionExportFolder(collectionId);
    setMessage(`导出目录：${result.status} ${result.path}`);
  }

  async function startFramePump() {
    if (busyAction) return;
    setBusyAction("frame-pump:start");
    try {
      const outputDir = primaryCollection?.watch_dir || primaryCollection?.input_dir || primaryCollection?.frame_pump_output_dir || undefined;
      const status = await apiClient.startV3FramePump({ fps: 1, full_screen: true, source_mode: "screen", output_dir: outputDir });
      setFramePump(status);
      await load(false);
      setMessage(status.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function detectWindows(collection: V3CollectionSummary) {
    setBusyAction(`windows:${collection.collection_id}`);
    try {
      const nextWindows = await apiClient.listV3ActionWindows();
      setWindows(nextWindows);
      setMessage(nextWindows.length ? `检测到 ${nextWindows.length} 个可见窗口，请选择目标游戏窗口。` : "没有检测到可见窗口，请先打开游戏或测试窗口。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function bindTargetWindow(collection: V3CollectionSummary, windowInfo: V3TargetWindowInfo) {
    setBusyAction(`target:${collection.collection_id}`);
    try {
      const updated = await apiClient.updateV3CollectionTargetWindow(collection.collection_id, windowInfo);
      replaceCollection(updated);
      const nextHealth = await apiClient.getV3ActionHealth(collection.collection_id);
      setActionHealth(nextHealth);
      setMessage(`已绑定目标窗口：${windowInfo.title}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function focusTargetWindow(collection: V3CollectionSummary) {
    setBusyAction(`focus:${collection.collection_id}`);
    try {
      const result = await apiClient.focusV3TargetWindow(collection.collection_id);
      const nextHealth = await apiClient.getV3ActionHealth(collection.collection_id);
      setActionHealth(nextHealth);
      await load(false);
      setMessage(result.ok ? "目标窗口已切到前台。" : `目标窗口未能切到前台：${result.blocked_reason || "target_window_not_foreground"}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function stopFramePump() {
    if (busyAction) return;
    setBusyAction("frame-pump:stop");
    try {
      const status = await apiClient.stopV3FramePump();
      setFramePump(status);
      await load(false);
      setMessage(status.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
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
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder(primaryCollection?.collection_id)}>打开 OBS 输出目录</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void load()}>刷新输入状态</button>
        </div>
      </Card>

      <ObsFramePumpPanel collectionId={primaryCollection?.collection_id} outputDir={primaryCollection?.watch_dir || primaryCollection?.input_dir} onMessage={setMessage} />

      <Card title="Frame Pump" className="mt-4">
        <div className="grid gap-3 md:grid-cols-5">
          <Metric label="状态" value={framePumpStatusText(framePump?.status)} />
          <Metric label="输出目录" value={primaryCollection?.watch_dir || primaryCollection?.input_dir || framePump?.output_dir || inputStatus?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
          <Metric label="最近输出帧" value={framePump?.latest_frame || "暂无"} />
          <Metric label="最近输出时间" value={framePump?.latest_frame_time || "-"} />
          <Metric label="已输出帧数" value={String(framePump?.frame_count ?? 0)} />
        </div>
        <p className="mt-3 text-sm text-slate-400">
          {framePump?.message || "Frame Pump -> obs-output -> folder_watch -> OCR/去重/入库。当前链路不依赖 OBS WebSocket。"}
        </p>
        {framePump?.status === "stale" || inputStatus?.status === "stale" ? <p className="mt-2 text-sm text-amber-200">等待 Frame Pump 输出截图</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500" disabled={Boolean(busyAction)} onClick={() => void startFramePump()}>{busyAction === "frame-pump:start" ? "启动中..." : "启动 Frame Pump"}</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500" disabled={Boolean(busyAction) || !["running", "stale", "error"].includes(framePump?.status || "")} onClick={() => void stopFramePump()}>{busyAction === "frame-pump:stop" ? "停止中..." : "停止 Frame Pump"}</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder(primaryCollection?.collection_id)}>打开输出目录</button>
        </div>
      </Card>

      <p className="my-4 whitespace-pre-line text-sm text-slate-400">{message}</p>

      <div className="grid gap-4">
        {orderedCollections.length === 0 ? <Card title="暂无采集项目"><p className="text-sm text-slate-500">请先创建 WPS、WinMerge 或游戏采集项目。</p></Card> : null}
        {orderedCollections.map((collection) => {
          const sameCollectionHealth = primaryCollection?.collection_id === collection.collection_id ? actionHealth : null;
          const blockers = sameCollectionHealth?.blockers || [];
          return (
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

            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="text-sm font-semibold text-slate-200">AI 自动探索状态</p>
              <div className="mt-3 grid gap-3 md:grid-cols-4">
                <Metric label="AI 自动探索" value={collection.game_agent_status || "未启用"} />
                <Metric label="当前识别状态" value={collection.game_agent_state || "unknown"} />
                <Metric label="本轮动作尝试" value={`${collection.latest_round_action_attempt_count} 次`} />
                <Metric label="本轮成功执行" value={`${collection.latest_round_action_executed_count} 次`} />
                <Metric label="本轮被阻止" value={`${collection.latest_round_action_blocked_count} 次`} />
                <Metric label="累计动作尝试" value={`${collection.action_attempt_total} 次`} />
                <Metric label="累计成功执行" value={`${collection.action_executed_total} 次`} />
                <Metric label="累计被阻止" value={`${collection.action_blocked_total} 次`} />
                <Metric label="真实输入权限" value={collection.real_input_enabled ? "已开启" : "未开启"} />
                <Metric label="键盘输入" value={readinessText(collection.keyboard_input_ready || Boolean(sameCollectionHealth?.keyboard_input_ready))} />
                <Metric label="鼠标移动" value={readinessText(collection.mouse_move_ready || Boolean(sameCollectionHealth?.mouse_move_ready))} />
                <Metric label="鼠标点击" value={readinessText(collection.mouse_click_ready || Boolean(sameCollectionHealth?.mouse_click_ready))} />
                <Metric label="光标读取" value={collection.cursor_read_access_denied || sameCollectionHealth?.cursor_read_access_denied ? "拒绝访问" : readinessText(collection.cursor_read_ready || Boolean(sameCollectionHealth?.cursor_read_ready))} />
                <Metric label="目标窗口" value={targetWindowLabel(collection)} />
                <Metric label="目标窗口前台" value={readinessText(collection.target_window_foreground || Boolean(sameCollectionHealth?.target_window_foreground))} />
                <Metric label="当前前台窗口" value={foregroundWindowLabel(collection.current_foreground_window || sameCollectionHealth?.current_foreground_window)} />
              </div>
              {(collection.enable_game_agent || collection.enable_game_explorer) && !collection.target_window_found ? (
                <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                  尚未绑定目标游戏窗口。请先点击“检测窗口”，选择正在运行的游戏窗口；也可以手动切到游戏窗口后再继续采集。
                </p>
              ) : null}
              {collection.keyboard_input_ready && !collection.mouse_click_ready ? (
                <p className="mt-3 rounded-lg border border-sky-500/30 bg-sky-500/10 p-3 text-sm text-sky-100">
                  键盘输入已经可用，鼠标点击暂不可用。GetCursorPos 或鼠标点击异常不会阻止 WASD、热键、按住按键这类键盘动作。
                </p>
              ) : null}
              {!collection.real_input_enabled && (collection.enable_game_agent || collection.enable_game_explorer) ? (
                <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                  真实输入未开启。需要用 APP_SHOT_ALLOW_REAL_INPUT=1 重启后端后，WASD、鼠标视角和真实点击才会执行。
                  启动命令：cd D:\work\app-shot\model；$env:APP_SHOT_ALLOW_REAL_INPUT="1"；powershell -ExecutionPolicy Bypass -File .\start_v3_app_shot.ps1
                </p>
              ) : null}
              {collection.agent_config_missing ? (
                <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                  <p>该任务创建于旧版本，需要更新 AI 自动探索配置后才能自动操作。</p>
                  <button className="mt-2 rounded-lg border border-amber-300/40 px-3 py-2 text-sm text-amber-50" disabled={Boolean(busyAction)} onClick={() => void enableAgentAndContinue(collection)}>
                    启用 AI 自动探索并继续
                  </button>
                </div>
              ) : null}
              <div className="mt-3 grid gap-2 text-sm text-slate-400">
                <span>已启用能力：{collection.game_agent_enabled_capabilities?.join("、") || "无"}</span>
                <span>最近动作：{String(collection.latest_action?.action_type || collection.latest_action?.planned_action || "-")}</span>
                <span>最近动作原因：{String(collection.latest_action?.reason || "-")}</span>
                <span>最近阻止原因：{collection.latest_blocked_reason || "-"}</span>
                <span>Input Gateway 阻塞项：{blockers.join("、") || "-"}</span>
                <span>visual_diff_score：{String(collection.latest_action?.visual_diff_score ?? "-")}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500" disabled={Boolean(busyAction)} onClick={() => void detectWindows(collection)}>
                  {busyAction === `windows:${collection.collection_id}` ? "检测中..." : "检测窗口"}
                </button>
                <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-500" disabled={Boolean(busyAction) || !collection.target_window_found} onClick={() => void focusTargetWindow(collection)}>
                  {busyAction === `focus:${collection.collection_id}` ? "切换中..." : "尝试切到目标窗口"}
                </button>
              </div>
              {windows.length > 0 ? (
                <div className="mt-3 grid gap-2">
                  {windows.slice(0, 10).map((windowInfo) => (
                    <button
                      key={`${windowInfo.hwnd}-${windowInfo.pid || 0}`}
                      className="grid gap-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-left text-sm text-slate-300 hover:border-blue-500/50 disabled:cursor-not-allowed disabled:text-slate-600"
                      disabled={Boolean(busyAction)}
                      onClick={() => void bindTargetWindow(collection, windowInfo)}
                    >
                      <span className="font-semibold text-slate-100">{windowInfo.title || `窗口 ${windowInfo.hwnd}`}</span>
                      <span className="text-xs text-slate-500">PID {windowInfo.pid || "-"} · {windowInfo.process_name || "-"} · {windowInfo.foreground ? "当前前台" : "后台"}</span>
                    </button>
                  ))}
                </div>
              ) : null}
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <AgentToggle label="启用 AI 自动探索" checked={collection.enable_game_agent || collection.enable_game_explorer} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { enable_game_agent: value, enable_game_explorer: value, game_agent_mode: value ? "auto_explore" : "off" })} />
                <AgentToggle label="安全场景确认" checked={collection.safe_scene_confirmed || collection.safe_game_scene_confirmed} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { safe_scene_confirmed: value, safe_game_scene_confirmed: value })} />
                <AgentToggle label="允许 UI 点击" checked={collection.allow_ui_click} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_ui_click: value })} />
                <AgentToggle label="允许热键探索" checked={collection.allow_hotkeys} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_hotkeys: value })} />
                <AgentToggle label="允许 WASD 移动" checked={collection.allow_wasd} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_wasd: value, allow_wasd_mouse: value || collection.allow_mouse_look })} />
                <AgentToggle label="允许鼠标视角变化" checked={collection.allow_mouse_look} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_mouse_look: value, allow_wasd_mouse: value || collection.allow_wasd })} />
                <AgentToggle label="允许返回/关闭" checked={collection.allow_back_close} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_back_close: value })} />
                <AgentToggle label="允许地图/背包/仓库探索" checked={collection.allow_inventory_map_explore} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_inventory_map_explore: value })} />
                <AgentToggle label="允许训练场移动探索" checked={collection.allow_training_movement} disabled={Boolean(busyAction)} onChange={(value) => void updateAgentConfig(collection, { allow_training_movement: value })} />
              </div>
              <label className="mt-3 grid gap-1 text-sm text-slate-300">
                <span className="text-xs text-slate-500">动作间隔（毫秒）</span>
                <input
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500"
                  type="number"
                  min={300}
                  max={10000}
                  value={collection.action_interval_ms}
                  disabled={Boolean(busyAction)}
                  onChange={(event) => void updateAgentConfig(collection, { action_interval_ms: Math.max(300, Math.min(Number(event.target.value), 10000)) })}
                />
              </label>
            </div>

            {collection.continue_suggestion ? <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">{collection.continue_suggestion}</p> : null}

            <p className="mt-3 text-xs text-slate-500">
              动作预算只限制本轮自动操作次数，不代表有效截图数量。有效截图数量以去重后的累计有效图片为准。如果本轮未达标，可以继续采集，系统会自动跨轮去重并累计。
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <ActionButton icon={<Play size={15} />} label={busyAction === `continue:${collection.collection_id}` ? "启动中..." : "继续采集"} disabled={Boolean(busyAction)} onClick={() => void continueCollection(collection.collection_id)} />
              <ActionButton icon={<Square size={15} />} label={collection.status === "stopped" ? "已停止" : busyAction === `stop:${collection.collection_id}` ? "停止中..." : "停止项目"} disabled={Boolean(busyAction) || collection.status === "stopped"} onClick={() => void stopCollection(collection)} />
              <LinkButton icon={<Images size={15} />} label="查看累计图库" to={`/v3/collections/${collection.collection_id}/gallery`} />
              <LinkButton icon={<ClipboardList size={15} />} label="查看所有轮次" to={`/v3/collections/${collection.collection_id}/runs`} />
              <ActionButton icon={<Archive size={15} />} label={busyAction === `export:${collection.collection_id}` ? "正在导出..." : "导出最终有效图"} disabled={Boolean(busyAction)} onClick={() => void exportCollection(collection)} />
              <ActionButton
                icon={<Trash2 size={15} />}
                label={busyAction === `delete:${collection.collection_id}` ? "删除中..." : "删除项目"}
                disabled={Boolean(busyAction) || ["running", "collecting", "waiting_for_input", "waiting_for_input_timeout"].includes(collection.status)}
                onClick={() => void deleteCollection(collection)}
              />
              <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder(collection.collection_id)}>
                <FolderOpen size={15} />打开文件夹
              </button>
            </div>

            {exportResult?.collectionId === collection.collection_id ? (
              <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
                <pre className="whitespace-pre-wrap text-sm text-slate-300">{exportResult.text}</pre>
                <button className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openExportFolder(collection.collection_id)}>打开导出目录</button>
              </div>
            ) : null}

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
                    <button
                      className="rounded border border-red-500/30 px-2 py-1 text-red-100 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
                      disabled={Boolean(busyAction) || ["running", "waiting_for_input", "waiting_for_input_timeout"].includes(String(run.status))}
                      onClick={() => void deleteRun(String(run.run_id))}
                    >
                      删除轮次
                    </button>
                  </div>
                ))}
              </div>
            </details>
          </Card>
          );
        })}
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

function buildAgentConfigPayload(collection: V3CollectionSummary, patch: V3AgentConfigRequest = {}): V3AgentConfigRequest {
  const merged = {
    enable_game_agent: collection.enable_game_agent || collection.enable_game_explorer,
    enable_game_explorer: collection.enable_game_explorer,
    game_agent_mode: collection.game_agent_mode === "auto_explore" ? "auto_explore" : "off",
    allow_ui_click: collection.allow_ui_click,
    allow_hotkeys: collection.allow_hotkeys,
    allow_wasd: collection.allow_wasd,
    allow_mouse_look: collection.allow_mouse_look,
    allow_back_close: collection.allow_back_close,
    allow_inventory_map_explore: collection.allow_inventory_map_explore,
    allow_training_movement: collection.allow_training_movement,
    allow_wasd_mouse: collection.allow_wasd_mouse,
    safe_scene_confirmed: collection.safe_scene_confirmed,
    safe_game_scene_confirmed: collection.safe_game_scene_confirmed,
    action_interval_ms: collection.action_interval_ms,
    ...patch
  } satisfies Required<V3AgentConfigRequest>;

  if (merged.allow_wasd_mouse || merged.allow_wasd || merged.allow_mouse_look) {
    merged.allow_wasd_mouse = true;
  }
  const anyCapability = [
    merged.allow_ui_click,
    merged.allow_hotkeys,
    merged.allow_wasd,
    merged.allow_mouse_look,
    merged.allow_back_close,
    merged.allow_inventory_map_explore,
    merged.allow_training_movement,
    merged.allow_wasd_mouse
  ].some(Boolean);
  if (patch.enable_game_agent === false) {
    merged.enable_game_agent = false;
    merged.enable_game_explorer = false;
    merged.game_agent_mode = "off";
    merged.allow_ui_click = false;
    merged.allow_hotkeys = false;
    merged.allow_wasd = false;
    merged.allow_mouse_look = false;
    merged.allow_back_close = false;
    merged.allow_inventory_map_explore = false;
    merged.allow_training_movement = false;
    merged.allow_wasd_mouse = false;
    return merged;
  }
  if (anyCapability || merged.enable_game_agent || merged.enable_game_explorer) {
    merged.enable_game_agent = true;
    merged.enable_game_explorer = true;
    merged.game_agent_mode = "auto_explore";
  } else {
    merged.enable_game_agent = false;
    merged.enable_game_explorer = false;
    merged.game_agent_mode = "off";
  }
  return merged;
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

function readinessText(value?: boolean) {
  return value ? "可用" : "不可用";
}

function targetWindowLabel(collection: V3CollectionSummary) {
  if (!collection.target_window_hwnd && !collection.target_window_title) return "未绑定";
  const title = collection.target_window_title || `HWND ${collection.target_window_hwnd}`;
  if (!collection.target_window_found) return `${title}（未找到）`;
  return collection.target_window_foreground ? `${title}（前台）` : `${title}（后台）`;
}

function foregroundWindowLabel(value?: Record<string, unknown> | null) {
  if (!value) return "-";
  const title = value.title || value.window_title || value.name;
  const processName = value.process_name || value.process || value.exe;
  if (title && processName) return `${String(title)} / ${String(processName)}`;
  if (title) return String(title);
  if (processName) return String(processName);
  const hwnd = value.hwnd || value.window_handle;
  return hwnd ? `HWND ${String(hwnd)}` : "-";
}

function delay(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms));
}

function isDebugCollection(collection: V3CollectionSummary) {
  const text = `${collection.collection_id} ${collection.task_name || ""} ${collection.app_name || ""} ${collection.display_name || ""}`.toLowerCase();
  return ["smoke", "test", "demo", "v3_real_test", "wrong_language"].some((keyword) => text.includes(keyword));
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

function AgentToggle({ label, checked, onChange, disabled = false }: { label: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean }) {
  return (
    <label className={`flex min-h-10 items-center gap-2 rounded-lg border px-3 py-2 text-sm ${disabled ? "border-slate-800 text-slate-600" : "border-slate-800 bg-slate-950 text-slate-300"}`}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function ActionButton({ icon, label, onClick, disabled = false }: { icon: ReactNode; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${disabled ? "cursor-not-allowed border-slate-800 text-slate-500" : "border-blue-500/40 text-blue-100"}`}
      disabled={disabled}
      onClick={onClick}
    >
      {icon}{label}
    </button>
  );
}

function LinkButton({ icon, label, to }: { icon: ReactNode; label: string; to: string }) {
  return <Link className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={to}>{icon}{label}</Link>;
}
