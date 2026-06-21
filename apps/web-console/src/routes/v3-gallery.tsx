import { Copy, FolderOpen, Maximize2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ImageRecord, V3RunRecord } from "../lib/api-types";
import { labelRejectReason, labelRegionType, labelStatus, overlayLabels } from "../lib/labels";

const buckets = ["accepted", "rejected", "manual_review", "deleted", "pending"] as const;
const overlayKeys = ["ocr_boxes", "showui_candidates", "fusion_candidates", "blocked_candidates", "click_points"] as const;

type OverlayKey = (typeof overlayKeys)[number];

export function V3GalleryRoute() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [runId, setRunId] = useState(params.runId || searchParams.get("run_id") || "");
  const [images, setImages] = useState<V3ImageRecord[]>([]);
  const [bucket, setBucket] = useState<string>("accepted");
  const [selected, setSelected] = useState<V3ImageRecord | null>(null);
  const [message, setMessage] = useState("正在查找最近一个有图片的 run。");
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    ocr_boxes: true,
    showui_candidates: true,
    fusion_candidates: true,
    blocked_candidates: true,
    click_points: true
  });

  useEffect(() => {
    void loadRuns();
  }, []);

  async function loadRuns() {
    try {
      const nextRuns = await apiClient.listV3Runs();
      setRuns(nextRuns);
      if (params.runId || searchParams.get("run_id")) {
        await loadImages(params.runId || searchParams.get("run_id") || "");
        return;
      }
      for (const run of nextRuns.slice(0, 10)) {
        const nextImages = await apiClient.getV3Images(run.run_id);
        if (nextImages.length > 0) {
          setRunId(run.run_id);
          applyImages(nextImages);
          setMessage(`已自动加载最近一个有图片的 run：${run.run_id}`);
          return;
        }
      }
      const fallbackRun = nextRuns[0];
      setRunId(fallbackRun?.run_id || "");
      setImages([]);
      setSelected(null);
      setMessage(fallbackRun ? "最近 10 个 run 暂无图片，请选择其他 run 或先启动采集。" : "暂无 V3 run。");
    } catch (error) {
      setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function loadImages(nextRunId = runId) {
    if (!nextRunId) return;
    try {
      const nextImages = await apiClient.getV3Images(nextRunId);
      setRunId(nextRunId);
      applyImages(nextImages);
      setMessage(nextImages.length ? `已加载 ${nextImages.length} 张图片。` : "当前 run 没有图片。");
    } catch (error) {
      setMessage(`接口不可用或返回异常：${error instanceof Error ? error.message : String(error)}`);
    }
  }

  function applyImages(nextImages: V3ImageRecord[]) {
    setImages(nextImages);
    setSelected(nextImages.find((image) => image.bucket === "accepted") || nextImages[0] || null);
  }

  const filtered = useMemo(() => images.filter((image) => bucket === "all" || image.bucket === bucket), [images, bucket]);

  async function copyPath(path: string) {
    await navigator.clipboard?.writeText(path);
    setMessage(`已复制图片路径：${path}`);
  }

  async function reveal(image: V3ImageRecord) {
    const result = await apiClient.revealV3Image(runId, image.image_id);
    setMessage(`打开图片所在文件夹：${result.status} ${result.folder || result.path}`);
  }

  async function openRunFolder() {
    if (!runId) return;
    const result = await apiClient.openV3RunFolder(runId);
    setMessage(`打开 run 文件夹：${result.status} ${result.path}`);
  }

  function toggleOverlay(key: OverlayKey) {
    setOverlays((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <div>
      <PageHeader title="采集结果" description="按合格、已拒绝、待人工审核、已删除查看截图、路径、OCR 文本摘要和重复判定。" />
      <Card title="选择 run 与筛选" eyebrow="gallery controls">
        <div className="flex flex-wrap items-center gap-2">
          <select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={runId} onChange={(event) => void loadImages(event.target.value)}>
            <option value="">选择 run</option>
            {runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.config.app_name} - {run.run_id}
              </option>
            ))}
          </select>
          {["all", ...buckets].map((item) => (
            <button key={item} className={`rounded-lg border px-3 py-2 text-sm ${bucket === item ? "border-blue-500/50 bg-blue-500/10 text-blue-100" : "border-slate-700 text-slate-300"}`} onClick={() => setBucket(item)}>
              {item === "all" ? "全部" : `${labelStatus(item)}（${item}）`}
            </button>
          ))}
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openRunFolder()}>
            <FolderOpen size={15} className="mr-1 inline" />
            打开 run 文件夹
          </button>
        </div>
        <p className="mt-3 break-all text-sm text-slate-400">{message}</p>
      </Card>

      <Card title="最近 10 个 run" eyebrow="recent runs" className="mt-4">
        <div className="grid gap-2">
          {runs.slice(0, 10).map((run) => (
            <button key={run.run_id} className={`grid gap-2 rounded-lg border p-3 text-left md:grid-cols-[1fr_1.2fr_0.8fr_0.8fr] ${run.run_id === runId ? "border-blue-500/50 bg-blue-500/10" : "border-slate-800 bg-slate-950"}`} onClick={() => void loadImages(run.run_id)}>
              <span className="break-all font-mono text-xs text-blue-200">{run.run_id}</span>
              <span className="text-sm text-slate-200">{run.config.app_name}</span>
              <span className="text-sm text-slate-400">合格 {run.counts.accepted || 0} / 已拒绝 {run.counts.rejected || 0}</span>
              <span className="break-all text-xs text-slate-500">{run.config.save_root}</span>
            </button>
          ))}
          {runs.length === 0 ? <p className="text-sm text-slate-500">暂无 run。</p> : null}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_440px]">
        <Card title="缩略图" eyebrow={`${filtered.length} images`}>
          {filtered.length === 0 ? (
            <p className="text-sm text-slate-500">当前筛选没有图片。请选择其他分桶或其他 run。</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-4">
              {filtered.map((image) => (
                <button key={image.image_id} className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-left hover:border-blue-500/50" onClick={() => setSelected(image)}>
                  {image.file_exists === false ? (
                    <div className="grid aspect-video w-full place-items-center rounded border border-slate-800 bg-slate-900 text-xs text-slate-500">文件不存在</div>
                  ) : (
                    <img className="aspect-video w-full rounded border border-slate-800 object-cover" src={apiClient.getV3ImageThumbnailUrl(runId, image.image_id)} alt={image.image_id} />
                  )}
                  <p className="mt-2 truncate font-mono text-xs text-slate-300">{image.image_id}</p>
                  <p className="text-xs text-slate-500">分桶：{labelStatus(image.bucket)}（{image.bucket}）</p>
                  <p className="text-xs text-slate-500">拒绝原因：{labelRejectReason(image.reject_reason)}</p>
                  <p className="text-xs text-slate-500">截图原因：{String(image.meta.capture_reason || "-")}</p>
                  <p className="truncate text-xs text-slate-500">界面状态：{String(image.meta.ui_state_hint || "-")}</p>
                  <p className="truncate text-xs text-slate-500">本地路径：{image.absolute_path || image.path}</p>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card title="大图预览" eyebrow={selected?.image_id || "未选择"}>
          {selected ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {overlayKeys.map((key) => (
                  <button key={key} className={`rounded-lg border px-2.5 py-1.5 text-xs ${overlays[key] ? "border-blue-500/50 bg-blue-500/10 text-blue-100" : "border-slate-700 text-slate-400"}`} onClick={() => toggleOverlay(key)}>
                    {overlayLabels[key]}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-500">叠加层图例：OCR 文字框 / ShowUI 候选 / 融合候选 / 已阻断候选 / 点击点；候选区域：内容区域 / 界面控件区域 / 风险窗口区域。</p>
              {selected.file_exists === false ? (
                <div className="grid aspect-video place-items-center rounded-lg border border-slate-800 bg-slate-950 text-sm text-slate-500">图片文件不存在，无法预览。</div>
              ) : (
                <div className="relative overflow-hidden rounded-lg border border-slate-800 bg-black">
                  <img className="w-full" src={apiClient.getV3ImagePreviewUrl(runId, selected.image_id)} alt={selected.image_id} />
                  <Overlay image={selected} overlays={overlays} />
                </div>
              )}
              <Detail label="图片 ID（image_id）" value={selected.image_id} />
              <Detail label="本地绝对路径" value={selected.absolute_path || selected.path} />
              <Detail label="拒绝原因（reject_reason）" value={labelRejectReason(selected.reject_reason)} />
              <Detail label="截图原因（capture_reason）" value={String(selected.meta.capture_reason || "-")} />
              <Detail label="界面状态（ui_state_hint）" value={String(selected.meta.ui_state_hint || "-")} />
              <Detail label="重复判定原因（duplicate_decision_reason）" value={String(selected.duplicate_decision?.duplicate_decision_reason || "-")} />
              <Detail label="OCR 文本摘要" value={ocrSummary(selected)} />
              <Detail label="动作 ID（action_id）" value={String(selected.meta.action_id || "-")} />
              <Detail label="候选区域类型（candidate_region_type）" value={labelRegionType(String(selected.meta.candidate_region_type || "unknown"))} />
              <div className="flex flex-wrap gap-2">
                <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void copyPath(selected.absolute_path || selected.path)}>
                  <Copy size={15} className="mr-1 inline" />
                  复制图片路径
                </button>
                <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void reveal(selected)}>
                  <FolderOpen size={15} className="mr-1 inline" />
                  打开图片所在文件夹
                </button>
                <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${runId}/actions`}>
                  <Maximize2 size={15} className="mr-1 inline" />
                  查看运行审计
                </Link>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">当前筛选没有图片。</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function Overlay({ image, overlays }: { image: V3ImageRecord; overlays: Record<OverlayKey, boolean> }) {
  const boxes = overlayBoxes(image, overlays);
  return (
    <>
      {boxes.map((box, index) => (
        <div
          key={`${box.kind}-${index}`}
          className={`pointer-events-none absolute border-2 ${boxClass(box.kind)}`}
          style={{ left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%` }}
          title={`${box.label}: ${box.text || ""}`}
        />
      ))}
    </>
  );
}

function overlayBoxes(image: V3ImageRecord, overlays: Record<OverlayKey, boolean>) {
  const sources: Array<[OverlayKey, unknown]> = [
    ["ocr_boxes", image.meta.ocr_boxes],
    ["showui_candidates", image.meta.showui_candidates],
    ["fusion_candidates", image.meta.fusion_candidates],
    ["blocked_candidates", image.meta.blocked_candidates],
    ["click_points", image.meta.click_points]
  ];
  const boxes: Array<{ kind: string; label: string; x: number; y: number; w: number; h: number; text?: string }> = [];
  for (const [key, raw] of sources) {
    if (!overlays[key]) continue;
    const items = Array.isArray(raw) ? raw : raw ? [raw] : [];
    for (const item of items) {
      if (!item || typeof item !== "object") continue;
      const candidate = item as { bbox?: number[]; x?: number; y?: number; text?: string; label?: string; candidate_region_type?: string; blocked?: boolean };
      const bbox = Array.isArray(candidate.bbox) && candidate.bbox.length >= 4 ? candidate.bbox : typeof candidate.x === "number" && typeof candidate.y === "number" ? [candidate.x - 6, candidate.y - 6, candidate.x + 6, candidate.y + 6] : null;
      if (!bbox) continue;
      const [x1, y1, x2, y2] = bbox;
      boxes.push({
        kind: candidate.blocked ? "blocked_candidates" : candidate.candidate_region_type || key,
        label: overlayLabels[key],
        x: Math.max(0, Math.min(100, x1 / 12)),
        y: Math.max(0, Math.min(100, y1 / 7)),
        w: Math.max(2, Math.min(100, (x2 - x1) / 12)),
        h: Math.max(2, Math.min(100, (y2 - y1) / 7)),
        text: candidate.text || candidate.label
      });
    }
  }
  return boxes;
}

function boxClass(kind: string) {
  if (kind.includes("unsafe_chrome") || kind.includes("blocked")) return "border-red-400";
  if (kind.includes("ui_chrome") || kind.includes("fusion")) return "border-emerald-400";
  if (kind.includes("content_area")) return "border-amber-400";
  if (kind.includes("click_points")) return "border-fuchsia-400";
  return "border-blue-400";
}

function ocrSummary(image: V3ImageRecord) {
  const value = image.meta.ocr_text || image.meta.text || image.meta.ocr_summary;
  if (typeof value === "string" && value.trim()) return value.slice(0, 240);
  return "-";
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="break-all font-mono text-xs text-slate-300">{value}</p>
    </div>
  );
}
