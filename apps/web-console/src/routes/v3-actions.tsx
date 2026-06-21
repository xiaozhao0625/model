import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ActionRecord, V3ImageRecord, V3RunRecord } from "../lib/api-types";
import { labelRegionType } from "../lib/labels";

export function V3ActionsRoute() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [runId, setRunId] = useState(params.runId || searchParams.get("run_id") || "");
  const [actions, setActions] = useState<V3ActionRecord[]>([]);
  const [images, setImages] = useState<V3ImageRecord[]>([]);

  async function loadRuns() {
    const nextRuns = await apiClient.listV3Runs();
    setRuns(nextRuns);
    const nextRunId = runId || nextRuns[0]?.run_id || "";
    setRunId(nextRunId);
    if (nextRunId) await loadDetails(nextRunId);
  }

  async function loadDetails(nextRunId = runId) {
    if (!nextRunId) return;
    const [nextActions, nextImages] = await Promise.all([apiClient.getV3Actions(nextRunId), apiClient.getV3Images(nextRunId)]);
    setActions(nextActions);
    setImages(nextImages);
  }

  useEffect(() => {
    void loadRuns();
  }, []);

  const imagesByPath = useMemo(() => {
    const map = new Map<string, V3ImageRecord>();
    for (const image of images) {
      map.set(image.path, image);
      if (image.absolute_path) map.set(image.absolute_path, image);
    }
    return map;
  }, [images]);

  return (
    <div>
      <PageHeader title="动作前后对比" description="每个真实动作都展示点之前、点之后、为什么点、有没有成功、有没有回退、有没有被拦截。" />
      <Card title="选择运行" eyebrow="run selector">
        <select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={runId} onChange={(event) => void (setRunId(event.target.value), loadDetails(event.target.value))}>
          {runs.map((run) => (
            <option key={run.run_id} value={run.run_id}>
              {run.config.app_name} - {run.run_id}
            </option>
          ))}
        </select>
      </Card>

      <div className="mt-4 grid gap-4">
        {actions.length === 0 ? <Card title="暂无动作"><p className="text-sm text-slate-500">当前 run 暂无 actions.jsonl 记录。</p></Card> : null}
        {actions.map((action, index) => {
          const before = imageFor(action.before_image, imagesByPath);
          const after = imageFor(action.after_image, imagesByPath);
          const result = (action.result || {}) as Record<string, unknown>;
          const safety = action.safety_result || {};
          const region = String((action as unknown as { candidate_region_type?: string }).candidate_region_type || safety.candidate_region_type || "unknown");
          const riskTerms = safety.risk_terms || safety.risk_flags || result.risk_terms || [];
          return (
            <Card key={`${action.source_candidate_id || action.label || "action"}-${index}`} title={`动作 ${index + 1}: ${action.label || "未命名"}`} eyebrow={String(result.status || "action")}>
              <div className="grid gap-4 xl:grid-cols-[1fr_1fr_360px]">
                <ImagePanel title="点之前（before_image）" image={before} rawPath={action.before_image} runId={runId} />
                <ImagePanel title="点之后（after_image）" image={after} rawPath={action.after_image} runId={runId} />
                <div className="space-y-2 text-sm">
                  <Detail label="action_id" value={String((action as unknown as { action_id?: string }).action_id || index + 1)} />
                  <Detail label="点击目标文字" value={action.label || "-"} />
                  <Detail label="click_x / click_y" value={Array.isArray(result.clicked) ? result.clicked.join(", ") : "-"} />
                  <Detail label="click_backend" value={String(result.click_backend || "-")} />
                  <Detail label="safety_result" value={JSON.stringify(safety)} />
                  <Detail label="result" value={JSON.stringify(result)} />
                  <Detail label="candidate_region_type" value={`${labelRegionType(region)} (${region})`} />
                  <Detail label="blocked_reason" value={String((action as unknown as { blocked_reason?: string }).blocked_reason || result.reason || "-")} />
                  <Detail label="risk_terms" value={Array.isArray(riskTerms) ? riskTerms.join(", ") : String(riskTerms || "-")} />
                  <Detail label="为什么点" value={String(result.reason || safety.reason || action.source_candidate_id || "-")} />
                  <Detail label="有没有成功" value={result.executed ? "已执行" : "未执行或被阻断"} />
                  <Detail label="有没有回退" value={String(result.rollback_reason || "-")} />
                  <Detail label="有没有被拦截" value={String(safety.allowed === false || result.status === "blocked" || result.status === "stopped")} />
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ImagePanel({ title, image, rawPath, runId }: { title: string; image?: V3ImageRecord; rawPath?: string | null; runId: string }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-slate-200">{title}</p>
      {image ? (
        <Link to={`/v3/runs/${runId}/gallery?image_id=${image.image_id}`}>
          <img className="aspect-video w-full rounded-lg border border-slate-800 object-cover" src={apiClient.getV3ImagePreviewUrl(runId, image.image_id)} alt={image.image_id} />
        </Link>
      ) : (
        <div className="grid aspect-video place-items-center rounded-lg border border-dashed border-slate-800 text-xs text-slate-500">图片不可用/未配置</div>
      )}
      <p className="mt-2 break-all font-mono text-xs text-slate-500">{image?.absolute_path || image?.path || rawPath || "-"}</p>
    </div>
  );
}

function imageFor(path: string | null | undefined, images: Map<string, V3ImageRecord>) {
  if (!path) return undefined;
  return images.get(path);
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="break-all font-mono text-xs text-slate-300">{value}</p>
    </div>
  );
}
