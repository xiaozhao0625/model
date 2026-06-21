import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ActionRecord, V3ImageRecord, V3RunRecord } from "../lib/api-types";
import { labelField, labelRegionType } from "../lib/labels";

export function V3ActionsRoute() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [runId, setRunId] = useState(params.runId || searchParams.get("run_id") || "");
  const [actions, setActions] = useState<V3ActionRecord[]>([]);
  const [images, setImages] = useState<V3ImageRecord[]>([]);
  const [message, setMessage] = useState("正在查找最近一个有动作审计的 run。");

  useEffect(() => {
    void loadRuns();
  }, []);

  async function loadRuns() {
    try {
      const nextRuns = await apiClient.listV3Runs();
      setRuns(nextRuns);
      const requested = params.runId || searchParams.get("run_id") || "";
      if (requested) {
        await loadDetails(requested);
        return;
      }
      for (const run of nextRuns.slice(0, 10)) {
        const nextActions = await apiClient.getV3Actions(run.run_id);
        if (nextActions.length > 0) {
          const nextImages = await apiClient.getV3Images(run.run_id);
          setRunId(run.run_id);
          setActions(nextActions);
          setImages(nextImages);
          setMessage(`已自动加载最近一个有动作审计的 run：${run.run_id}`);
          return;
        }
      }
      setRunId(nextRuns[0]?.run_id || "");
      setMessage(nextRuns.length ? "最近 10 个 run 暂无动作审计记录。" : "暂无 V3 run。");
    } catch (error) {
      setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function loadDetails(nextRunId = runId) {
    if (!nextRunId) return;
    try {
      const [nextActions, nextImages] = await Promise.all([apiClient.getV3Actions(nextRunId), apiClient.getV3Images(nextRunId)]);
      setRunId(nextRunId);
      setActions(nextActions);
      setImages(nextImages);
      setMessage(nextActions.length ? `已加载 ${nextActions.length} 条动作审计。` : "当前 run 暂无动作审计记录。");
    } catch (error) {
      setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`);
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
      <PageHeader title="运行审计" description="展示动作 ID、目标、执行结果、阻断原因、风险词、候选区域类型，以及点击前截图和点击后截图。" />
      <Card title="选择 run" eyebrow="run selector">
        <div className="flex flex-wrap items-center gap-2">
          <select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={runId} onChange={(event) => void loadDetails(event.target.value)}>
            <option value="">选择 run</option>
            {runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.config.app_name} - {run.run_id}
              </option>
            ))}
          </select>
          {runId ? (
            <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${runId}/gallery`}>
              查看采集结果
            </Link>
          ) : null}
        </div>
        <p className="mt-3 text-sm text-slate-400">{message}</p>
      </Card>

      <div className="mt-4 grid gap-4">
        {actions.length === 0 ? <Card title="暂无动作"><p className="text-sm text-slate-500">当前 run 暂无 meta/actions.jsonl 记录。</p></Card> : null}
        {actions.map((action, index) => {
          const before = imageFor(action.before_image, imagesByPath);
          const after = imageFor(action.after_image, imagesByPath);
          const result = (action.result || {}) as Record<string, unknown>;
          const safety = action.safety_result || {};
          const region = String((action as unknown as { candidate_region_type?: string }).candidate_region_type || safety.candidate_region_type || "unknown");
          const riskTerms = safety.risk_terms || safety.risk_flags || result.risk_terms || [];
          const actionId = String((action as unknown as { action_id?: string }).action_id || action.source_candidate_id || index + 1);
          const blocked = safety.allowed === false || result.status === "blocked" || result.status === "stopped" || result.executed === false;
          return (
            <Card key={`${actionId}-${index}`} title={`动作 ${index + 1}: ${action.label || "未命名目标"}`} eyebrow={String(result.status || "action")}>
              <div className="grid gap-4 xl:grid-cols-[1fr_1fr_360px]">
                <ImagePanel title="点之前：点击前截图（before_image）" image={before} rawPath={action.before_image} runId={runId} />
                <ImagePanel title="点之后：点击后截图（after_image）" image={after} rawPath={action.after_image} runId={runId} />
                <div className="space-y-2 text-sm">
                  <Detail label="动作 ID（action_id）" value={actionId} />
                  <Detail label="点击目标文字" value={action.label || "-"} />
                  <Detail label="执行结果" value={result.executed ? "已执行" : blocked ? "已阻断或未执行" : "未执行"} />
                  <Detail label={`${labelField("click_backend")}（click_backend）`} value={String(result.click_backend || "-")} />
                  <Detail label={`${labelField("candidate_region_type")}（candidate_region_type）`} value={`${labelRegionType(region)}（${region}）`} />
                  <Detail label={`${labelField("blocked_reason")}（blocked_reason）`} value={String((action as unknown as { blocked_reason?: string }).blocked_reason || result.reason || "-")} />
                  <Detail label={`${labelField("risk_terms")}（risk_terms）`} value={Array.isArray(riskTerms) ? riskTerms.join(", ") || "-" : String(riskTerms || "-")} />
                  <Detail label="为什么点" value={String(result.reason || safety.reason || action.source_candidate_id || "-")} />
                  <Detail label="有没有成功" value={result.executed ? "是，已执行" : "否，未执行或被阻断"} />
                  <Detail label="有没有回退" value={String(result.rollback_reason || "-")} />
                  <Detail label="有没有被拦截" value={blocked ? "是" : "否"} />
                  <details className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                    <summary className="cursor-pointer text-xs text-slate-400">高级调试：原始动作 JSON</summary>
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

function ImagePanel({ title, image, rawPath, runId }: { title: string; image: V3ImageRecord | null; rawPath?: string | null; runId: string }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-slate-200">{title}</p>
      {image && image.file_exists !== false ? (
        <img className="aspect-video w-full rounded-lg border border-slate-800 object-cover" src={apiClient.getV3ImagePreviewUrl(runId, image.image_id)} alt={image.image_id} />
      ) : (
        <div className="grid aspect-video place-items-center rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-500">{image?.file_exists === false ? "截图文件不存在" : "没有匹配到截图"}</div>
      )}
      <p className="mt-2 break-all font-mono text-xs text-slate-500">{rawPath || "-"}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-all text-xs text-slate-300">{value}</p>
    </div>
  );
}
