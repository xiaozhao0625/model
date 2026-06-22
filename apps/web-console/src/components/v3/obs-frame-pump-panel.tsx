import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Card } from "../ui/card";
import { apiClient } from "../../lib/api-client";
import type {
  V3FramePumpStartRequest,
  V3FramePumpStatus,
  V3InputStatus,
  V3ObsConfigRequest,
  V3ObsSceneOption,
  V3ObsSourceOption,
  V3ObsStatus
} from "../../lib/api-types";

const inputClass = "rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500";

export function ObsFramePumpPanel({ onMessage }: { onMessage?: (message: string) => void }) {
  const [obsConfig, setObsConfig] = useState<V3ObsConfigRequest>({ obs_host: "127.0.0.1", obs_port: 4455, obs_password: "", screenshot_target: "source", image_format: "png" });
  const [sourceMode, setSourceMode] = useState<NonNullable<V3FramePumpStartRequest["source_mode"]>>("obs_websocket");
  const [fps, setFps] = useState(1);
  const [obs, setObs] = useState<V3ObsStatus | null>(null);
  const [scenes, setScenes] = useState<V3ObsSceneOption[]>([]);
  const [sources, setSources] = useState<V3ObsSourceOption[]>([]);
  const [framePump, setFramePump] = useState<V3FramePumpStatus | null>(null);
  const [input, setInput] = useState<V3InputStatus | null>(null);
  const [message, setMessage] = useState("");
  const [previewVersion, setPreviewVersion] = useState(0);

  useEffect(() => {
    void refresh();
  }, []);

  function show(text: string) {
    setMessage(text);
    onMessage?.(text);
  }

  async function refresh() {
    const [nextObs, nextFramePump, nextInput] = await Promise.all([
      apiClient.getV3ObsStatus(obsConfig),
      apiClient.getV3FramePumpStatus(),
      apiClient.getV3InputStatus()
    ]);
    setObs(nextObs);
    setFramePump(nextFramePump);
    setInput(nextInput);
    setPreviewVersion(Date.now());
  }

  async function testObs() {
    try {
      const result = await apiClient.getV3ObsStatus(obsConfig);
      setObs(result);
      show(result.connected ? `OBS WebSocket 已连接，当前场景：${result.current_scene || "-"}` : result.error || "未连接 OBS WebSocket。");
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  async function loadScenes() {
    try {
      const result = await apiClient.getV3ObsScenes(obsConfig);
      setScenes(result.scenes);
      show(`已读取 ${result.scenes.length} 个 OBS 场景。`);
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  async function loadSources() {
    try {
      const result = await apiClient.getV3ObsSources({ ...obsConfig, scene_name: obsConfig.obs_scene_name });
      setSources(result.sources);
      show(`已读取 ${result.sources.length} 个 OBS 来源。`);
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  async function testScreenshot() {
    try {
      const result = await apiClient.testV3ObsScreenshot(obsConfig);
      await refresh();
      show(result.message || result.image_path || "测试截图完成。");
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  async function startFramePump() {
    try {
      const payload: V3FramePumpStartRequest = { ...obsConfig, source_mode: sourceMode, fps, full_screen: true };
      const result = await apiClient.startV3FramePump(payload);
      setFramePump(result);
      await refresh();
      show(result.message);
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  async function stopFramePump() {
    try {
      const result = await apiClient.stopV3FramePump();
      setFramePump(result);
      await refresh();
      show(result.message);
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  async function openOutputDir() {
    try {
      const result = await apiClient.openV3InputFolder();
      show(`输出目录：${result.path}`);
    } catch (error) {
      show(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <Card title="OBS / Frame Pump 控制" className="mt-4">
      <div className="grid gap-3 md:grid-cols-4">
        <Field label="OBS 地址"><input className={inputClass} value={obsConfig.obs_host || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_host: event.target.value })} /></Field>
        <Field label="OBS WebSocket 端口"><input className={inputClass} type="number" value={obsConfig.obs_port || 4455} onChange={(event) => setObsConfig({ ...obsConfig, obs_port: Number(event.target.value) })} /></Field>
        <Field label="OBS 密码"><input className={inputClass} type="password" value={obsConfig.obs_password || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_password: event.target.value })} /></Field>
        <Field label="截图目标"><select className={inputClass} value={obsConfig.screenshot_target || "source"} onChange={(event) => setObsConfig({ ...obsConfig, screenshot_target: event.target.value as V3ObsConfigRequest["screenshot_target"] })}><option value="source">指定来源</option><option value="scene">整个场景</option></select></Field>
        <Field label="场景"><input className={inputClass} list="v3-obs-scenes" value={obsConfig.obs_scene_name || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_scene_name: event.target.value })} /><datalist id="v3-obs-scenes">{scenes.map((scene) => <option key={obsOptionName(scene)} value={obsOptionName(scene)} />)}</datalist></Field>
        <Field label="来源"><input className={inputClass} list="v3-obs-sources" value={obsConfig.obs_source_name || ""} onChange={(event) => setObsConfig({ ...obsConfig, obs_source_name: event.target.value })} /><datalist id="v3-obs-sources">{sources.map((source) => <option key={obsOptionName(source)} value={obsOptionName(source)} />)}</datalist></Field>
        <Field label="输入源模式"><select className={inputClass} value={sourceMode} onChange={(event) => setSourceMode(event.target.value as NonNullable<V3FramePumpStartRequest["source_mode"]>)}><option value="obs_websocket">OBS WebSocket（推荐）</option><option value="obs_projector">OBS 投影窗口</option><option value="screen">当前屏幕</option><option value="window">指定窗口</option></select></Field>
        <Field label="FPS"><select className={inputClass} value={fps} onChange={(event) => setFps(Number(event.target.value))}><option value={1}>1 FPS</option><option value={2}>2 FPS</option><option value={5}>5 FPS</option></select></Field>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-5">
        <Metric label="OBS WebSocket" value={obs?.connected ? "已连接" : "未连接"} />
        <Metric label="Frame Pump" value={framePumpStatusText(framePump?.status)} />
        <Metric label="输出目录" value={framePump?.output_dir || input?.watch_dir || "D:\\work\\app-shot\\obs-output"} />
        <Metric label="最近输出帧" value={framePump?.latest_frame || input?.latest_file || "暂无"} />
        <Metric label="已输出帧数" value={String(framePump?.frame_count ?? 0)} />
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-[220px_1fr]">
        <div className="h-32 overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
          {framePump?.latest_frame_path ? <img className="h-full w-full object-contain" src={`${apiClient.getV3FramePumpLatestFrameUrl()}?v=${previewVersion}`} alt="最近输出帧预览" /> : <div className="flex h-full items-center justify-center text-sm text-slate-500">暂无预览</div>}
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm text-slate-400">
          <p>OBS WebSocket 负责取图；自动点击、WASD 和鼠标视角变化由 V3 输入网关执行。</p>
          <p className="mt-2">只截图模式不会执行动作。自动操作模式需要安全场景确认，且不会使用注入或绕过反作弊的方式后台控制游戏。</p>
          <p className="mt-2">最近输出时间：{framePump?.latest_frame_time || input?.latest_file_time || "-"}</p>
        </div>
      </div>

      {message ? <p className="mt-3 whitespace-pre-line text-sm text-amber-200">{message}</p> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={() => void testObs()}>连接测试</Button>
        <Button onClick={() => void loadScenes()}>读取场景列表</Button>
        <Button onClick={() => void loadSources()}>读取来源列表</Button>
        <Button onClick={() => void testScreenshot()}>测试截图</Button>
        <Button primary onClick={() => void startFramePump()}>启动 Frame Pump</Button>
        <Button onClick={() => void stopFramePump()}>停止 Frame Pump</Button>
        <Button onClick={() => void openOutputDir()}>打开输出目录</Button>
        <Button onClick={() => void refresh()}>刷新状态</Button>
      </div>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">{label}</span>{children}</label>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 break-all text-sm font-semibold text-slate-100">{value}</p></div>;
}

function Button({ children, onClick, primary = false }: { children: ReactNode; onClick: () => void; primary?: boolean }) {
  return <button className={`rounded-lg border px-3 py-2 text-sm ${primary ? "border-blue-500/40 bg-blue-500/10 text-blue-100" : "border-slate-700 text-slate-200"}`} onClick={onClick}>{children}</button>;
}

function obsOptionName(option: V3ObsSceneOption | V3ObsSourceOption) {
  return typeof option === "string" ? option : option.name;
}

function framePumpStatusText(status?: V3FramePumpStatus["status"]) {
  if (status === "running") return "运行中";
  if (status === "stale") return "等待输出";
  if (status === "error") return "异常";
  return "未运行";
}
