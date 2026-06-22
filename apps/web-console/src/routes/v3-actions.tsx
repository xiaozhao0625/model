import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ActionRecord, V3ImageRecord, V3RunRecord } from "../lib/api-types";
import { displayRunName, isDebugRun, labelRegionType } from "../lib/labels";

export function V3ActionsRoute() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [runId, setRunId] = useState(params.runId || searchParams.get("run_id") || "");
  const [actions, setActions] = useState<V3ActionRecord[]>([]);
  const [images, setImages] = useState<V3ImageRecord[]>([]);
  const [message, setMessage] = useState("正在读取动作审计。");

  useEffect(() => {
    void loadRuns();
  }, []);

  async function loadRuns() {
    try {
      const realRuns = (await apiClient.listV3Runs()).filter((run) => !isDebugRun(run));
      setRuns(realRuns);
      const requested = params.runId || searchParams.get("run_id") || realRuns[0]?.run_id || "";
      if (requested) await loadDetails(requested);
      else setMessage("暂无真实任务。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function loadDetails(nextRunId = runId) {
    if (!nextRunId) return;
    try {
      const [nextActions, nextImages] = await Promise.all([apiClient.getV3Actions(nextRunId), apiClient.getV3Images(nextRunId)]);
      setRunId(nextRunId);
      setActions(nextActions);
      setImages(nextImages);
      setMessage(nextActions.length ? `已加载 ${nextActions.length} 条动作审计。` : "当前任务暂无动作审计记录。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  const imagesByPath = useMemo(() => {
    const map = new Map<string, V3ImageRecord>();
    for (const image of images) {
      map.set(image.path, image);
      if (image.absolute_path) map.set(image.absolute_path, image);
      map.set(image.image_id, image);
    }
    return map;
  }, [images]);

  return (
    <div>
      <PageHeader title="运行详情 / 审计" description="查看候选区域、安全判断、点击结果、动作前后截图和 actions.jsonl 记录。" />
      <Card title="选择任务">
        <div className="flex flex-wrap items-center gap-2">
          <select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={runId} onChange={(event) => void loadDetails(event.target.value)}>
            <option value="">选择任务</option>
            {runs.map((run) => <option key={run.run_id} value={run.run_id}>{displayRunName(run)} - {run.config.app_name}</option>)}
          </select>
          {runId ? <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${runId}/gallery`}>查看结果图库</Link> : null}
        </div>
        <p className="mt-3 text-sm text-slate-400">{message}</p>
      </Card>

      <div className="mt-4 grid gap-4">
        {actions.length === 0 ? <Card title="暂无动作"><p className="text-sm text-slate-500">当前任务暂无动作审计记录。</p></Card> : null}
        {actions.map((action, index) => {
          const before = imageFor(action.before_image, imagesByPath);
          const after = imageFor(action.after_image, imagesByPath);
          const result = action.result || {};
          const safety = action.safety_result || {};
          const region = String((action as unknown as { candidate_region_type?: string }).candidate_region_type || safety.candidate_region_type || "unknown");
          const blocked = safety.allowed === false || result.status === "blocked" || result.status === "stopped" || result.executed === false;
          return (
            <Card key={`${action.source_candidate_id || index}`} title={`动作 ${index + 1}: ${action.label || "未命名目标"}`} eyebrow={blocked ? "已阻止或未执行" : "已执行"}>
              <div className="grid gap-4 xl:grid-cols-[1fr_1fr_360px]">
                <ImagePanel title="动作前截图" image={before} rawPath={action.before_image} runId={runId} />
                <ImagePanel title="动作后截图" image={after} rawPath={action.after_image} runId={runId} />
                <div className="space-y-2">
                  <Detail label="执行结果" value={result.executed ? "已执行" : "未执行或被阻止"} />
                  <Detail label="候选区域类型" value={labelRegionType(region)} />
                  <Detail label="阻止原因" value={String((action as unknown as { blocked_reason?: string }).blocked_reason || result.reason || safety.reason || "-")} />
                  <Detail label="点击通道" value={String(result.click_backend || "-")} />
                  <Detail label="风险词" value={riskText(safety, result)} />
                  <Detail label="回退原因" value={String(result.rollback_reason || "-")} />
                  <details className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                    <summary className="cursor-pointer text-xs text-slate-400">高级调试信息：原始动作 JSON</summary>
                    <pre className="mt-2 max-h-56 overflow-auto text-xs text-slate-500">{JSON.stringify(action, null, 2)}</pre>
                  </details>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function imageFor(path: string | null | undefined, images: Map<string, V3ImageRecord>) {
  if (!path) return null;
  return images.get(path) || images.get(path.split("\\").join("/")) || null;
}

function riskText(safety: Record<string, unknown>, result: Record<string, unknown>) {
  const value = safety.risk_terms || safety.risk_flags || result.risk_terms || [];
  return Array.isArray(value) ? value.join(", ") || "-" : String(value || "-");
}

function ImagePanel({ title, image, rawPath, runId }: { title: string; image: V3ImageRecord | null; rawPath?: string | null; runId: string }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-slate-200">{title}</p>
      {image && image.file_exists !== false ? <img className="aspect-video w-full rounded-lg border border-slate-800 object-cover" src={apiClient.getV3ImagePreviewUrl(runId, image.image_id)} alt={image.image_id} /> : <div className="grid aspect-video place-items-center rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-500">没有匹配到截图</div>}
      <p className="mt-2 break-all text-xs text-slate-500">{rawPath || "-"}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 break-all text-xs text-slate-300">{value}</p></div>;
}
