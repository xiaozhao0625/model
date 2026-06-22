import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3TaskConfig } from "../lib/api-types";
import { gameActionPresetLabels, gameModeLabels, textPolicyLabels } from "../lib/labels";

const inputClass = "rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500";

export function V3GameRoute() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<V3TaskConfig | null>(null);
  const [message, setMessage] = useState("游戏采集默认文字优先，允许少量无文字补充图；动作默认关闭。");

  useEffect(() => {
    void apiClient.getV3Defaults().then((defaults) =>
      setConfig({
        ...defaults,
        task_name: "三角洲行动",
        app_name: "三角洲行动",
        display_name: "三角洲行动",
        app_type: "pc_game",
        target_language: "zh",
        target_accepted_min: 800,
        target_accepted_soft: 1000,
        target_accepted_max: 2000,
        max_images: 2000,
        max_actions: 20,
        max_game_actions: 50,
        game_mode: "menu",
        text_priority: true,
        must_have_text: true,
        allow_no_text_fill: true,
        no_text_fill_ratio: 0.1,
        text_policy: "text_priority_with_fill",
        enable_game_explorer: false,
        game_action_preset: "screenshot_only",
        allow_wasd_mouse: false,
        safe_game_scene_confirmed: false,
        observe_only: true,
        enable_auto_click: false
      })
    ).catch((error) => setMessage(error instanceof Error ? error.message : String(error)));
  }, []);

  function patch(next: Partial<V3TaskConfig>) {
    if (!config) return;
    setConfig({ ...config, ...next });
  }

  async function create(start: boolean) {
    if (!config) return;
    if ((config.enable_game_explorer || config.game_action_preset !== "screenshot_only") && !config.safe_game_scene_confirmed) {
      setMessage("启用游戏动作前，必须确认已经进入训练场、靶场、单机或局外安全页面。");
      return;
    }
    try {
      const created = await apiClient.createV3Collection({
        config: {
          ...config,
          display_name: config.display_name || config.task_name || config.app_name,
          max_game_actions: Math.min(config.max_game_actions, 200),
          no_text_fill_ratio: Math.min(config.no_text_fill_ratio, 0.2),
          observe_only: !config.enable_game_explorer && !config.enable_auto_click
        },
        start_immediately: start
      });
      const collectionId = "collection" in created ? created.collection.collection_id : created.collection_id;
      navigate("/v3/current", { replace: true, state: { collectionId } });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  if (!config) return <PageHeader title="游戏采集" description="正在读取默认配置。" />;

  return (
    <div>
      <PageHeader title="游戏采集" description="优先采集菜单、设置、背包、仓库、地图、装备、技能、任务、HUD、对话和结算等有文字界面。" />
      <div className="grid gap-4 xl:grid-cols-[1fr_0.7fr]">
        <Card title="新建游戏采集任务">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="任务名称"><input className={inputClass} value={config.task_name || ""} onChange={(event) => patch({ task_name: event.target.value, display_name: event.target.value })} /></Field>
            <Field label="游戏名称"><input className={inputClass} value={config.app_name} onChange={(event) => patch({ app_name: event.target.value })} /></Field>
            <Field label="游戏模式"><select className={inputClass} value={config.game_mode} onChange={(event) => patch({ game_mode: event.target.value as V3TaskConfig["game_mode"] })}>{Object.entries(gameModeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
            <Field label="目标语言"><select className={inputClass} value={config.target_language} onChange={(event) => patch({ target_language: event.target.value })}><option value="zh">中文</option><option value="en">英文</option><option value="ja">日文</option><option value="ko">韩文</option></select></Field>
            <Field label="文字策略"><select className={inputClass} value={config.text_policy} onChange={(event) => patch({ text_policy: event.target.value as V3TaskConfig["text_policy"] })}>{Object.entries(textPolicyLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
            <Field label="目标有效截图数"><input className={inputClass} type="number" value={config.target_accepted_min} onChange={(event) => patch({ target_accepted_min: Number(event.target.value) })} /></Field>
            <Field label="期望截图数"><input className={inputClass} type="number" value={config.target_accepted_soft} onChange={(event) => patch({ target_accepted_soft: Number(event.target.value) })} /></Field>
            <Field label="最大截图数"><input className={inputClass} type="number" value={config.max_images} onChange={(event) => patch({ max_images: Number(event.target.value) })} /></Field>
            <Field label="无文字补充图比例"><input className={inputClass} type="number" min={0} max={0.2} step={0.01} value={config.no_text_fill_ratio} onChange={(event) => patch({ no_text_fill_ratio: Math.min(Number(event.target.value), 0.2) })} /></Field>
            <Field label="游戏动作预设"><select className={inputClass} value={config.game_action_preset} onChange={(event) => patch({ game_action_preset: event.target.value as V3TaskConfig["game_action_preset"], enable_game_explorer: event.target.value !== "screenshot_only", allow_wasd_mouse: event.target.value === "wasd_mouse" })}>{Object.entries(gameActionPresetLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
            <Field label="最大游戏动作数"><input className={inputClass} type="number" max={200} value={config.max_game_actions} onChange={(event) => patch({ max_game_actions: Math.min(Number(event.target.value), 200) })} /></Field>
            <Field label="动作间隔"><input className={inputClass} type="number" value={config.action_interval_ms} onChange={(event) => patch({ action_interval_ms: Number(event.target.value) })} /></Field>
            <Toggle label="文字优先" checked={config.text_priority} onChange={(value) => patch({ text_priority: value })} />
            <Toggle label="严格必须有文字" checked={config.must_have_text} onChange={(value) => patch({ must_have_text: value })} />
            <Toggle label="允许少量无文字补充图" checked={config.allow_no_text_fill} onChange={(value) => patch({ allow_no_text_fill: value })} />
            <Toggle label="启用游戏键鼠探索" checked={config.enable_game_explorer} onChange={(value) => patch({ enable_game_explorer: value })} />
          </div>
          <label className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-50">
            <input className="mt-1" type="checkbox" checked={config.safe_game_scene_confirmed} onChange={(event) => patch({ safe_game_scene_confirmed: event.target.checked })} />
            <span>我已手动进入训练场、靶场、单机、局外背包/仓库/地图等安全场景；系统不会自动登录、充值、匹配、排位或聊天。</span>
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void create(false)}>创建任务</button>
            <button className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-2 text-sm text-blue-100" onClick={() => void create(true)}>创建并开始采集</button>
          </div>
          <p className="mt-3 text-sm text-slate-400">{message}</p>
        </Card>
        <Card title="游戏安全边界">
          <ul className="space-y-2 text-sm text-slate-300">
            {["默认只截图，不操作", "启用 WASD / 鼠标视角变化必须由用户明确选择", "禁止自动登录、验证码、充值、购买、匹配、排位、聊天", "无文字图只能作为视觉补充图，并受比例限制", "风险页面和高风险按钮必须被 Safety Gate 阻止"].map((item) => <li key={item} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">{item}</li>)}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="grid gap-1 text-sm text-slate-300"><span className="text-xs text-slate-500">{label}</span>{children}</label>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />{label}</label>;
}
