import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3CollectionSummary, V3FramePumpStatus, V3Health, V3InputStatus, V3ObsConfigRequest, V3ObsSceneOption, V3ObsSourceOption, V3ObsStatus, V3RunRecord } from "../lib/api-types";
import { isDebugRun, labelStatus } from "../lib/labels";

type State = {
  health: V3Health | null;
  input: V3InputStatus | null;
  framePump: V3FramePumpStatus | null;
  obs: V3ObsStatus | null;
  scenes: V3ObsSceneOption[];
  sources: V3ObsSourceOption[];
  runs: V3RunRecord[];
  collections: V3CollectionSummary[];
  error: string | null;
};

export function ToolHealthRoute() {
  const [state, setState] = useState<State>({ health: null, input: null, framePump: null, obs: null, scenes: [], sources: [], runs: [], collections: [], error: null });
  const [obsConfig, setObsConfig] = useState<V3ObsConfigRequest>({ obs_host: "127.0.0.1", obs_port: 4455, obs_password: "", screenshot_target: "source", image_format: "png" });
  const [frameFps, setFrameFps] = useState(1);
  const [obsMessage, setObsMessage] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [health, input, framePump, obs, runs, collections] = await Promise.all([
        apiClient.getV3Health(),
        apiClient.getV3InputStatus(),
        apiClient.getV3FramePumpStatus(),
        apiClient.getV3ObsStatus(obsConfig),
        apiClient.listV3Runs(),
        apiClient.listV3Collections()
      ]);
      setState((current) => ({ ...current, health, input, framePump, obs, runs: runs.filter((run) => !isDebugRun(run)), collections, error: null }));
    } catch (error) {
      setState({ health: null, input: null, framePump: null, obs: null, scenes: [], sources: [], runs: [], collections: [], error: error instanceof Error ? error.message : String(error) });
    }
  }

  async function startFramePump() {
    await apiClient.startV3FramePump({ fps: frameFps, full_screen: true, source_mode: "obs_websocket", ...obsConfig });
    await load();
  }

  async function stopFramePump() {
    await apiClient.stopV3FramePump();
    await load();
  }

  async function openInputFolder() {
    await apiClient.openV3InputFolder();
  }

  async function testObs() {
    const obs = await apiClient.getV3ObsStatus(obsConfig);
    setState((current) => ({ ...current, obs }));
    setObsMessage(obs.message);
  }

  async function loadScenes() {
    const result = await apiClient.getV3ObsScenes(obsConfig);
    setState((current) => ({ ...current, scenes: result.scenes }));
    setObsMessage(`已读取 ${result.scenes.length} 个 OBS 场景。`);
  }

  async function loadSources() {
    const result = await apiClient.getV3ObsSources({ ...obsConfig, scene_name: obsConfig.obs_scene_name });
    setState((current) => ({ ...current, sources: result.sources }));
    setObsMessage(`已读取 ${result.sources.length} 个 OBS 来源。`);
  }

  async function testScreenshot() {
    const result = await apiClient.testV3ObsScreenshot(obsConfig);
    await load();
    setObsMessage(result.message || result.image_path || "测试截图完成。");
  }

  const health = state.health;
  const collectingCollections = useMemo(() => state.collections.filter((item) => item.status === "collecting").length, [state.collections]);
  const activeRuns = useMemo(() => state.runs.filter((run) => run.collection_id && ["running", "waiting_for_input", "waiting_for_input_timeout"].includes(run.status)).length, [state.runs]);
  const recentErrors = useMemo(() => state.runs.map((run) => run.last_error).filter(Boolean).slice(0, 5), [state.runs]);
  const paddle = health?.ocr?.find((item) => item.provider === "paddleocr");
  const showui = health?.models?.find((item) => item.provider === "showui");
  const screenshotReady = Boolean(health && state.input?.exists && state.framePump?.status === "running" && paddle?.status === "ready");
  const fullAutoRequested = Boolean(health?.defaults?.enable_auto_click || health?.defaults?.enable_game_explorer);

  return (
    <div>
      <PageHeader title="系统状态" description="检查本机 V3 采集所需组件。V3 单机截图采集不需要 Redis、PostgreSQL 或 Docker。" />
      {state.error ? <Card title="接口异常"><p className="text-sm text-red-200">{state.error}</p></Card> : null}

      <Card title="采集可用性" className="mb-4">
        <div className="grid gap-3 md:grid-cols-3">
          <StatusCard label="截图采集链路" value={screenshotReady ? "可用" : "不可用"} tone={screenshotReady ? "ok" : "warn"} note="后端、前端、OBS 目录、OCR 基础能力。" />
          <StatusCard label="完整自动操作链路" value={health?.full_auto_capture_ready ? "可用" : fullAutoRequested ? "未就绪" : "未启用"} tone={health?.full_auto_capture_ready ? "ok" : "neutral"} note="只有自动点击、键鼠探索需要 ShowUI 和 Input Gateway。" />
          <StatusCard label="当前采集中项目" value={`${collectingCollections} 个 collection / ${activeRuns} 个 run`} tone="ok" note="只统计真实 collection 下正在运行或等待输入的轮次。" />
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatusCard label="后端 API" value={health ? "正常" : "异常"} tone={health ? "ok" : "bad"} />
        <StatusCard label="前端" value="正常" tone="ok" />
        <StatusCard label="OBS 输入目录" value={labelStatus(state.input?.status)} tone={state.input?.exists ? "ok" : "bad"} />
        <StatusCard label="PaddleOCR" value={paddle?.status === "ready" ? "正常" : "异常"} tone={paddle?.status === "ready" ? "ok" : "bad"} />
        <StatusCard label="OCR GPU" value={health?.ocr_gpu_ready ? "已启用" : "未启用 CPU 模式"} tone="neutral" note="截图采集可用；GPU 只是加速项。" />
        <StatusCard label="ShowUI" value={showui?.status === "ready" && showui.enabled ? "正常" : "可选未就绪"} tone="neutral" note={showui?.reason || "只在自动操作链路中需要。"} />
        <StatusCard label="Input Gateway" value={health?.input_gateway_ready ? "正常" : "可选未就绪"} tone="neutral" note={health?.input_gateway_blockers?.join("；") || "只在自动点击/键鼠操作中需要。"} />
        <StatusCard label="FFmpeg" value="已检测" tone="ok" />
        <StatusCard label="OBS" value={state.input?.exists ? "已检测" : "目录不存在"} tone={state.input?.exists ? "ok" : "bad"} />
        <StatusCard label="防息屏" value={String(health?.power_policy?.status || "unknown")} tone="neutral" />
        <StatusCard label="采集项目数" value={String(state.collections.length)} tone="ok" />
        <StatusCard label="历史未归类 run" value={String(state.runs.filter((run) => !run.collection_id).length)} tone="neutral" />
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

      <Card title="OBS WebSocket 截图" className="mt-4">
        <div className="grid gap-3 md:grid-cols-4">
          <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">Host</span><input className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={obsConfig.obs_host || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_host: event.target.value })} /></label>
          <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">Port</span><input className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" type="number" value={obsConfig.obs_port || 4455} onChange={(event) => setObsConfig({ ...obsConfig, obs_port: Number(event.target.value) })} /></label>
          <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">Password</span><input className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" type="password" value={obsConfig.obs_password || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_password: event.target.value })} /></label>
          <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">FPS</span><select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={frameFps} onChange={(event) => setFrameFps(Number(event.target.value))}><option value={1}>1 FPS</option><option value={2}>2 FPS</option><option value={5}>5 FPS</option></select></label>
          <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">场景</span><input className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" list="obs-scenes" value={obsConfig.obs_scene_name || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_scene_name: event.target.value })} /><datalist id="obs-scenes">{state.scenes.map((scene) => <option key={obsOptionName(scene)} value={obsOptionName(scene)} />)}</datalist></label>
          <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">来源</span><input className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" list="obs-sources" value={obsConfig.obs_source_name || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_source_name: event.target.value })} /><datalist id="obs-sources">{state.sources.map((source) => <option key={obsOptionName(source)} value={obsOptionName(source)} />)}</datalist></label>
          <Field label="连接状态" value={state.obs?.connected ? "已连接" : "未连接"} />
          <Field label="当前来源模式" value={state.framePump?.source_mode || state.framePump?.mode || "-"} />
        </div>
        <p className="mt-3 text-sm text-slate-400">OBS WebSocket 只用于截取 OBS 画面，不负责录制、推流、改场景，也不执行游戏操作。游戏操作仍由 Input Gateway 安全门控。</p>
        {obsMessage ? <p className="mt-2 whitespace-pre-line text-sm text-amber-200">{obsMessage}</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void testObs()}>测试连接</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void loadScenes()}>读取场景</button>
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void loadSources()}>读取来源</button>
          <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void testScreenshot()}>测试截图</button>
        </div>
      </Card>

      <Card title="Frame Pump" className="mt-4">
        <div className="grid gap-3 md:grid-cols-5">
          <Field label="状态" value={framePumpStatusText(state.framePump?.status)} />
          <Field label="输出目录" value={state.framePump?.output_dir || state.input?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
          <Field label="最近输出帧" value={state.framePump?.latest_frame || "暂无"} />
          <Field label="最近输出时间" value={state.framePump?.latest_frame_time || "-"} />
          <Field label="已输出帧数" value={String(state.framePump?.frame_count ?? 0)} />
        </div>
        <p className="mt-3 text-sm text-slate-400">
          {state.framePump?.message || "Frame Pump -> obs-output -> folder_watch -> OCR/去重/入库；不依赖 OBS WebSocket。"}
        </p>
        {state.framePump?.status === "stale" || state.input?.status === "stale" ? <p className="mt-2 text-sm text-amber-200">等待 Frame Pump 输出截图</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void startFramePump()}>启动 Frame Pump</button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void stopFramePump()}>停止 Frame Pump</button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openInputFolder()}>打开输出目录</button>
        </div>
      </Card>

      <Card title="自动操作链路说明" className="mt-4">
        <p className="text-sm text-slate-300">
          OCR GPU、ShowUI、Input Gateway 属于自动点击或键鼠探索链路。只截图、OBS 文件夹采集、OCR 过滤和 collection 去重不依赖这些能力。
          当前页面不再把它们显示为阻塞性异常；只有你开启自动操作时，它们才需要处理。
        </p>
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

function StatusCard({ label, value, tone, note }: { label: string; value: string; tone: "ok" | "warn" | "bad" | "neutral"; note?: string }) {
  const color = tone === "ok" ? "text-emerald-200" : tone === "bad" ? "text-red-200" : tone === "warn" ? "text-amber-200" : "text-slate-200";
  return (
    <Card>
      <p className="text-sm font-semibold text-slate-100">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${color}`}>{value}</p>
      {note ? <p className="mt-2 text-xs leading-5 text-slate-500">{note}</p> : null}
    </Card>
  );
}

function framePumpStatusText(status?: V3FramePumpStatus["status"]) {
  if (status === "running") return "运行中";
  if (status === "stale" || status === "error") return "异常";
  return "未运行";
}

function Field({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 break-all text-sm text-slate-200">{value}</p></div>;
}

function obsOptionName(option: V3ObsSceneOption | V3ObsSourceOption) {
  return typeof option === "string" ? option : option.name;
}
