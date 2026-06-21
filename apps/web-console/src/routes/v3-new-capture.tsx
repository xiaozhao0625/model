import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3TaskConfig } from "../lib/api-types";

const inputClass = "rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-500";

export function V3NewCaptureRoute() {
  const [config, setConfig] = useState<V3TaskConfig | null>(null);
  const [message, setMessage] = useState("配置软件采集任务，默认仅观察，不自动点击。");
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);

  useEffect(() => {
    void apiClient
      .getV3Defaults()
      .then((defaults) =>
        setConfig({
          ...defaults,
          app_type: "pc_app",
          target_language: "en",
          observe_only: true,
          enable_auto_click: false,
          must_have_text: true,
          max_images: 300,
          max_actions: 20
        })
      )
      .catch((error) => setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`));
  }, []);

  async function createRun() {
    if (!config) return;
    try {
      const run = await apiClient.createV3Run({ config });
      setCreatedRunId(run.run_id);
      setMessage(`已创建采集任务：${run.run_id}`);
    } catch (error) {
      setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  if (!config) {
    return (
      <div>
        <PageHeader title="新建采集" description="正在读取 V3 默认配置。" />
        <p className="text-sm text-slate-400">{message}</p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="新建采集" description="创建软件采集任务，OBS/folder_watch 输入目录固定使用 D:\\work\\app-shot\\obs-output。" />
      <Card title="软件采集配置" eyebrow="pc_app">
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="软件名称">
            <input className={inputClass} value={config.app_name} onChange={(event) => setConfig({ ...config, app_name: event.target.value })} />
          </Field>
          <Field label="目标语言">
            <select className={inputClass} value={config.target_language} onChange={(event) => setConfig({ ...config, target_language: event.target.value })}>
              {["en", "ja", "ko", "zh"].map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </Field>
          <Field label="最大截图数">
            <input className={inputClass} type="number" value={config.max_images} onChange={(event) => setConfig({ ...config, max_images: Number(event.target.value) })} />
          </Field>
          <Field label="最大动作数">
            <input className={inputClass} type="number" value={config.max_actions} onChange={(event) => setConfig({ ...config, max_actions: Number(event.target.value) })} />
          </Field>
          <Toggle label="允许自动点击（enable_auto_click）" checked={config.enable_auto_click} onChange={(value) => setConfig({ ...config, enable_auto_click: value, observe_only: !value })} />
          <Toggle label="必须有文字（must_have_text）" checked={config.must_have_text} onChange={(value) => setConfig({ ...config, must_have_text: value })} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void createRun()}>
            创建软件采集任务
          </button>
          {createdRunId ? (
            <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${createdRunId}/gallery`}>
              查看结果
            </Link>
          ) : null}
        </div>
        <p className="mt-3 text-sm text-slate-400">{message}</p>
      </Card>
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
