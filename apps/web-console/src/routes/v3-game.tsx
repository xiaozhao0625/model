import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3TaskConfig } from "../lib/api-types";
import { gameModeLabels } from "../lib/labels";

const inputClass = "rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500";

export function V3GameRoute() {
  const [config, setConfig] = useState<V3TaskConfig | null>(null);
  const [windowTitle, setWindowTitle] = useState("");
  const [processName, setProcessName] = useState("");
  const [message, setMessage] = useState("游戏采集默认不允许自动探索，只有用户明确开启键鼠探索（enable_game_explorer）才允许。");
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);

  useEffect(() => {
    void apiClient
      .getV3Defaults()
      .then((defaults) =>
        setConfig({
          ...defaults,
          app_name: "game_sample",
          app_type: "pc_game",
          target_language: "en",
          game_mode: "menu",
          allow_no_text_gameplay: false,
          enable_game_explorer: false,
          enable_auto_click: false,
          observe_only: true,
          must_have_text: true,
          max_images: 300,
          max_actions: 10,
          max_game_actions: 10
        })
      )
      .catch((error) => setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`));
  }, []);

  function setGameMode(gameMode: V3TaskConfig["game_mode"]) {
    if (!config) return;
    const gameplay = gameMode === "gameplay";
    setConfig({
      ...config,
      game_mode: gameMode,
      allow_no_text_gameplay: gameplay,
      must_have_text: !gameplay
    });
  }

  async function createGameRun() {
    if (!config) return;
    try {
      const run = await apiClient.createV3Run({
        config: {
          ...config,
          app_name: `${config.app_name}${windowTitle ? `:${windowTitle}` : ""}${processName ? `:${processName}` : ""}`
        }
      });
      setCreatedRunId(run.run_id);
      setMessage(`已创建游戏采集任务：${run.run_id}`);
    } catch (error) {
      setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  if (!config) {
    return <PageHeader title="游戏采集" description="正在读取默认配置。" />;
  }

  return (
    <div>
      <PageHeader title="游戏采集" description="游戏菜单模式使用文字语言过滤；游戏对局模式允许无文字，但必须通过画面变化过滤和 Safety Gate。" />
      <div className="grid gap-4 xl:grid-cols-[1fr_0.75fr]">
        <Card title="新建游戏采集任务" eyebrow="pc_game">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="游戏名称">
              <input className={inputClass} value={config.app_name} onChange={(event) => setConfig({ ...config, app_name: event.target.value })} />
            </Field>
            <Field label="游戏窗口标题">
              <input className={inputClass} value={windowTitle} onChange={(event) => setWindowTitle(event.target.value)} />
            </Field>
            <Field label="进程名">
              <input className={inputClass} value={processName} onChange={(event) => setProcessName(event.target.value)} />
            </Field>
            <Field label="目标语言">
              <select className={inputClass} value={config.target_language} onChange={(event) => setConfig({ ...config, target_language: event.target.value })}>
                {["en", "ja", "ko", "zh"].map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="采集模式">
              <select className={inputClass} value={config.game_mode} onChange={(event) => setGameMode(event.target.value as V3TaskConfig["game_mode"])}>
                {Object.entries(gameModeLabels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="最大游戏动作数（max_game_actions）">
              <input className={inputClass} type="number" value={config.max_game_actions} onChange={(event) => setConfig({ ...config, max_game_actions: Number(event.target.value) })} />
            </Field>
            <Toggle label="是否允许无文字对局（allow_no_text_gameplay）" checked={config.allow_no_text_gameplay} onChange={(value) => setConfig({ ...config, allow_no_text_gameplay: value, must_have_text: !value })} />
            <Toggle label="键鼠探索（enable_game_explorer）" checked={config.enable_game_explorer} onChange={(value) => setConfig({ ...config, enable_game_explorer: value })} />
          </div>
          <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
            游戏菜单模式：文字语言过滤。游戏对局模式：画面变化过滤。自动判断：先识别菜单/对局状态，再选择过滤策略。允许 no_text，但必须非黑屏、非白屏、非 near_duplicate、变化明显且不触发风险。
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void createGameRun()}>
              创建游戏采集任务
            </button>
            {createdRunId ? (
              <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${createdRunId}/gallery`}>
                查看结果
              </Link>
            ) : null}
          </div>
          <p className="mt-3 text-sm text-slate-400">{message}</p>
        </Card>

        <Card title="安全提示" eyebrow="game safety">
          <ul className="space-y-2 text-sm text-slate-300">
            {["禁止登录", "禁止验证码", "禁止充值", "禁止购买", "禁止匹配真人", "禁止排位", "禁止聊天", "禁止绕过反作弊"].map((item) => (
              <li key={item} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
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
    <label className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}
