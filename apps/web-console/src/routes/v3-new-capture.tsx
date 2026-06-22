import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { ObsFramePumpPanel } from "../components/v3/obs-frame-pump-panel";
import { apiClient } from "../lib/api-client";
import type { V3TaskConfig } from "../lib/api-types";
import { gameActionPresetLabels, gameModeLabels, textPolicyLabels } from "../lib/labels";

const inputClass = "rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500";
type Tab = "software" | "game" | "advanced";

export function V3NewCaptureRoute() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("software");
  const [config, setConfig] = useState<V3TaskConfig | null>(null);
  const [message, setMessage] = useState("正在读取默认配置。");

  useEffect(() => {
    void apiClient
      .getV3Defaults()
      .then((defaults) =>
        setConfig({
          ...defaults,
          task_name: "wps",
          app_name: "WPS",
          display_name: "wps",
          app_type: "pc_app",
          target_language: "zh",
          target_accepted_min: 800,
          target_accepted_soft: 1000,
          target_accepted_max: 2000,
          capture_source: "obs_websocket",
          max_images: 1500,
          max_actions: 20,
          max_game_actions: 50,
          observe_only: true,
          enable_auto_click: false,
          text_priority: true,
          must_have_text: true,
          allow_no_text_fill: false,
          no_text_fill_ratio: 0,
          text_policy: "strict_text",
          game_action_preset: "screenshot_only",
          allow_wasd_mouse: false,
          safe_game_scene_confirmed: false
        })
      )
      .catch((error) => setMessage(error instanceof Error ? error.message : String(error)));
  }, []);

  function patch(next: Partial<V3TaskConfig>) {
    if (!config) return;
    const merged = { ...config, ...next };
    if (next.text_policy === "strict_text") {
      merged.must_have_text = true;
      merged.allow_no_text_fill = false;
      merged.no_text_fill_ratio = 0;
    }
    if (next.text_policy === "text_priority_with_fill" && merged.no_text_fill_ratio <= 0) {
      merged.allow_no_text_fill = true;
      merged.no_text_fill_ratio = 0.1;
    }
    if (next.game_action_preset === "screenshot_only") {
      merged.enable_game_explorer = false;
      merged.allow_wasd_mouse = false;
      merged.enable_auto_click = false;
      merged.observe_only = true;
    }
    if (next.game_action_preset === "wasd_mouse") {
      merged.enable_game_explorer = true;
      merged.allow_wasd_mouse = true;
    }
    if (next.allow_wasd_mouse === true) {
      merged.enable_game_explorer = true;
    }
    setConfig(merged);
  }

  function applyTab(next: Tab) {
    setTab(next);
    if (!config) return;
    if (next === "software") {
      patch({
        app_type: "pc_app",
        task_name: config.task_name || "wps",
        app_name: config.app_name || "WPS",
        display_name: config.display_name || config.task_name || config.app_name || "wps",
        max_images: config.max_images || 1500,
        max_actions: Math.min(config.max_actions || 20, 100),
        capture_source: "obs_websocket",
        must_have_text: true,
        allow_no_text_fill: false,
        no_text_fill_ratio: 0,
        text_policy: "strict_text",
        observe_only: !config.enable_auto_click
      });
    }
    if (next === "game") {
      patch({
        app_type: "pc_game",
        task_name: config.task_name || "游戏采集",
        app_name: config.app_name || "游戏",
        display_name: config.display_name || config.task_name || config.app_name || "游戏采集",
        max_images: Math.max(config.max_images || 0, 2000),
        max_actions: Math.min(config.max_actions || 20, 100),
        max_game_actions: Math.min(config.max_game_actions || 50, 200),
        capture_source: "obs_websocket",
        game_mode: "menu",
        text_priority: true,
        must_have_text: true,
        allow_no_text_fill: true,
        no_text_fill_ratio: 0.1,
        text_policy: "text_priority_with_fill",
        enable_game_explorer: false,
        game_action_preset: "screenshot_only",
        allow_wasd_mouse: false
      });
    }
  }

  function validate(next: V3TaskConfig) {
    if ((next.app_type === "pc_game" || next.app_type === "game") && next.max_game_actions > 200) {
      return "最大动作数是自动点击或键鼠动作次数，不是截图数量。为了安全，游戏动作最多允许 200 次。";
    }
    if (next.max_actions > 100) {
      return "最大动作数是自动点击或键鼠动作次数，不是截图数量。为了安全，单次任务最多允许 100 次软件动作。";
    }
    if (next.no_text_fill_ratio > 0.2) {
      return "无文字补充图比例最多 20%。";
    }
    if ((next.game_action_preset === "wasd_mouse" || next.enable_game_explorer) && !next.safe_game_scene_confirmed) {
      return "启用游戏键鼠探索前，必须确认已经进入训练场、靶场、单机或局外安全页面。";
    }
    return "";
  }

  async function createRun(startImmediately: boolean) {
    if (!config) return;
    const prepared = {
      ...config,
      display_name: config.display_name || config.task_name || config.app_name,
      observe_only: !config.enable_auto_click && !config.enable_game_explorer,
      max_actions: Math.min(config.max_actions, 100),
      max_game_actions: Math.min(config.max_game_actions, 200)
    };
    if (prepared.text_policy === "strict_text") {
      prepared.must_have_text = true;
      prepared.allow_no_text_fill = false;
      prepared.no_text_fill_ratio = 0;
    }
    if (prepared.game_action_preset === "screenshot_only") {
      prepared.enable_game_explorer = false;
      prepared.allow_wasd_mouse = false;
      prepared.enable_auto_click = false;
      prepared.observe_only = true;
    }
    const validation = validate(prepared);
    if (validation) {
      setMessage(validation);
      return;
    }
    try {
      const created = await apiClient.createV3Collection({ config: prepared, start_immediately: startImmediately });
      const collectionId = "collection" in created ? created.collection.collection_id : created.collection_id;
      setMessage(startImmediately ? "采集项目已创建，并开始第一轮采集等待 OBS 输入。" : "采集项目已创建。");
      navigate("/v3/current", { replace: true, state: { collectionId } });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  if (!config) {
    return (
      <div>
        <PageHeader title="新建采集任务" description="正在读取本机 V3 配置。" />
        <p className="text-sm text-slate-400">{message}</p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="新建采集任务" description="创建软件或游戏采集任务，OBS 输出目录固定为 D:\\work\\app-shot\\obs-output。" />
      <div className="mb-4 flex flex-wrap gap-2">
        <TabButton active={tab === "software"} onClick={() => applyTab("software")} label="软件采集" />
        <TabButton active={tab === "game"} onClick={() => applyTab("game")} label="游戏采集" />
        <TabButton active={tab === "advanced"} onClick={() => applyTab("advanced")} label="高级配置" />
      </div>

      <ObsFramePumpPanel onMessage={setMessage} />

      <Card title={tab === "game" ? "游戏采集" : tab === "advanced" ? "高级配置" : "软件采集"}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="任务名称">
            <input className={inputClass} value={config.task_name || ""} onChange={(event) => patch({ task_name: event.target.value, display_name: event.target.value })} />
          </Field>
          <Field label={tab === "game" ? "游戏名称" : "软件名称"}>
            <input className={inputClass} value={config.app_name} onChange={(event) => patch({ app_name: event.target.value })} />
          </Field>
          <Field label="应用类型">
            <select className={inputClass} value={config.app_type} onChange={(event) => patch({ app_type: event.target.value as V3TaskConfig["app_type"] })}>
              <option value="pc_app">PC 软件</option>
              <option value="pc_game">PC 游戏</option>
              <option value="web">网页</option>
              <option value="auto">自动判断</option>
            </select>
          </Field>
          <Field label="截图来源">
            <select className={inputClass} value={config.capture_source} onChange={(event) => patch({ capture_source: event.target.value as V3TaskConfig["capture_source"] })}>
              <option value="obs_websocket">OBS WebSocket 截图</option>
              <option value="screen">全屏截图</option>
              <option value="window">目标窗口截图</option>
              <option value="folder_watch">只监听 obs-output 文件夹</option>
            </select>
          </Field>
          <Field label="目标语言">
            <select className={inputClass} value={config.target_language} onChange={(event) => patch({ target_language: event.target.value })}>
              <option value="zh">中文</option>
              <option value="en">英文</option>
              <option value="ja">日文</option>
              <option value="ko">韩文</option>
            </select>
          </Field>
          <Field label="目标有效截图数">
            <input className={inputClass} type="number" min={1} max={5000} value={config.target_accepted_min} onChange={(event) => patch({ target_accepted_min: Number(event.target.value) })} />
          </Field>
          <Field label="期望截图数">
            <input className={inputClass} type="number" min={1} max={5000} value={config.target_accepted_soft} onChange={(event) => patch({ target_accepted_soft: Number(event.target.value) })} />
          </Field>
          <Field label="最大截图数">
            <input className={inputClass} type="number" min={1} max={50000} value={config.max_images} onChange={(event) => patch({ max_images: Number(event.target.value) })} />
          </Field>
          {tab !== "game" && config.app_type !== "pc_game" ? (
            <Field label="最大软件动作数">
              <input className={inputClass} type="number" min={0} max={100} value={config.max_actions} onChange={(event) => patch({ max_actions: Math.min(Number(event.target.value), 100) })} />
            </Field>
          ) : null}

          {tab === "game" || config.app_type === "pc_game" ? (
            <>
              <Field label="游戏模式">
                <select className={inputClass} value={config.game_mode} onChange={(event) => patch({ game_mode: event.target.value as V3TaskConfig["game_mode"] })}>
                  {Object.entries(gameModeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                </select>
              </Field>
              <Field label="文字策略">
                <select className={inputClass} value={config.text_policy} onChange={(event) => patch({ text_policy: event.target.value as V3TaskConfig["text_policy"] })}>
                  {Object.entries(textPolicyLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                </select>
              </Field>
              <Field label="无文字补充图比例">
                <input className={inputClass} type="number" min={0} max={0.2} step={0.01} value={config.no_text_fill_ratio} onChange={(event) => patch({ no_text_fill_ratio: Math.min(Number(event.target.value), 0.2) })} />
              </Field>
              <Field label="最大游戏动作数">
                <input className={inputClass} type="number" min={0} max={200} value={config.max_game_actions} onChange={(event) => patch({ max_game_actions: Math.min(Number(event.target.value), 200) })} />
              </Field>
              <Field label="游戏动作预设">
                <select className={inputClass} value={config.game_action_preset} onChange={(event) => patch({ game_action_preset: event.target.value as V3TaskConfig["game_action_preset"], enable_game_explorer: event.target.value !== "screenshot_only", allow_wasd_mouse: event.target.value === "wasd_mouse" })}>
                  {Object.entries(gameActionPresetLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                </select>
              </Field>
              <Field label="动作间隔">
                <input className={inputClass} type="number" min={200} max={60000} value={config.action_interval_ms} onChange={(event) => patch({ action_interval_ms: Number(event.target.value) })} />
              </Field>
            </>
          ) : null}

          <Toggle label="允许自动点击" checked={config.enable_auto_click} onChange={(value) => patch({ enable_auto_click: value, observe_only: !value })} />
          <Toggle label="文字优先" checked={config.text_priority} onChange={(value) => patch({ text_priority: value })} />
          <Toggle label="严格必须有文字" checked={config.must_have_text} onChange={(value) => patch({ must_have_text: value })} />
          <Toggle label="允许少量无文字补充图" checked={config.allow_no_text_fill} onChange={(value) => patch({ allow_no_text_fill: value })} />
          <Toggle label="启用游戏键鼠探索" checked={config.enable_game_explorer} onChange={(value) => patch({ enable_game_explorer: value })} />
          <Toggle label="允许 WASD / 鼠标视角变化" checked={config.allow_wasd_mouse} onChange={(value) => patch({ allow_wasd_mouse: value })} />
        </div>

        {(tab === "game" || config.app_type === "pc_game") ? (
          <label className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-50">
            <input className="mt-1" type="checkbox" checked={config.safe_game_scene_confirmed} onChange={(event) => patch({ safe_game_scene_confirmed: event.target.checked })} />
            <span>我已手动进入训练场、靶场、单机、局外背包/仓库/地图等安全场景；系统不会自动登录、充值、匹配、排位或聊天。</span>
          </label>
        ) : null}

        <details className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-3">
          <summary className="cursor-pointer text-sm text-slate-300">高级调试信息</summary>
          <pre className="mt-3 max-h-80 overflow-auto text-xs text-slate-500">{JSON.stringify(config, null, 2)}</pre>
        </details>

        <div className="mt-4 flex flex-wrap gap-2">
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void createRun(false)}>创建任务</button>
          <button className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-2 text-sm text-blue-100" onClick={() => void createRun(true)}>创建并开始采集</button>
        </div>
        <p className="mt-3 whitespace-pre-line text-sm text-slate-400">{message}</p>
      </Card>
    </div>
  );
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return <button className={`rounded-lg border px-3 py-2 text-sm ${active ? "border-blue-500/50 bg-blue-500/10 text-blue-100" : "border-slate-700 text-slate-300"}`} onClick={onClick}>{label}</button>;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1 text-sm text-slate-300">
      <span className="text-xs text-slate-500">{label}</span>
      {children}
    </label>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex min-h-10 items-center gap-2 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}
