import { Copy, FolderOpen } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ImageRecord, V3RunRecord } from "../lib/api-types";
import { labelRejectReason, labelRegionType, labelStatus } from "../lib/labels";

const buckets = ["accepted", "rejected", "manual_review", "deleted", "pending"] as const;

export function V3GalleryRoute() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [runId, setRunId] = useState(params.runId || searchParams.get("run_id") || "");
  const [images, setImages] = useState<V3ImageRecord[]>([]);
  const [bucket, setBucket] = useState<string>("accepted");
  const [selected, setSelected] = useState<V3ImageRecord | null>(null);
  const [message, setMessage] = useState("选择 run 后查看采集结果图库。");
  const [overlay, setOverlay] = useState(true);

  async function loadRuns() {
    const nextRuns = await apiClient.listV3Runs();
    setRuns(nextRuns);
    const nextRunId = runId || nextRuns[0]?.run_id || "";
    setRunId(nextRunId);
    if (nextRunId) {
      await loadImages(nextRunId);
    }
  }

  async function loadImages(nextRunId = runId) {
    if (!nextRunId) return;
    const nextImages = await apiClient.getV3Images(nextRunId);
    setImages(nextImages);
    setSelected(nextImages[0] || null);
    setMessage(`已加载 ${nextImages.length} 张图片。`);
  }

  useEffect(() => {
    void loadRuns();
  }, []);

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

  return (
    <div>
      <PageHeader title="采集结果图库" description="按 accepted / rejected / manual_review / deleted 查看截图、路径、OCR 摘要和重复判定。" />
      <Card title="筛选与路径" eyebrow="gallery controls">
        <div className="flex flex-wrap items-center gap-2">
          <select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={runId} onChange={(event) => void (setRunId(event.target.value), loadImages(event.target.value))}>
            {runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.config.app_name} - {run.run_id}
              </option>
            ))}
          </select>
          {["all", ...buckets].map((item) => (
            <button key={item} className={`rounded-lg border px-3 py-2 text-sm ${bucket === item ? "border-blue-500/50 bg-blue-500/10 text-blue-100" : "border-slate-700 text-slate-300"}`} onClick={() => setBucket(item)}>
              {item === "all" ? "全部" : `${labelStatus(item)} (${item})`}
            </button>
          ))}
          <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openRunFolder()}>
            <FolderOpen size={15} className="mr-1 inline" />
            打开 run 文件夹
          </button>
          <label className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300">
            <input type="checkbox" checked={overlay} onChange={(event) => setOverlay(event.target.checked)} />
            OCR bbox / ShowUI candidate / fusion candidate / blocked candidate overlay
          </label>
        </div>
        <p className="mt-3 break-all text-sm text-slate-400">{message}</p>
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card title="缩略图网格" eyebrow={`${filtered.length} images`}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-4">
            {filtered.map((image) => (
              <button key={image.image_id} className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-left hover:border-blue-500/50" onClick={() => setSelected(image)}>
                <img className="aspect-video w-full rounded border border-slate-800 object-cover" src={apiClient.getV3ImageThumbnailUrl(runId, image.image_id)} alt={image.image_id} />
                <p className="mt-2 truncate font-mono text-xs text-slate-300">{image.image_id}</p>
                <p className="text-xs text-slate-500">reject_reason: {labelRejectReason(image.reject_reason)}</p>
              </button>
            ))}
          </div>
        </Card>

        <Card title="大图预览" eyebrow={selected?.image_id || "未选择"}>
          {selected ? (
            <div className="space-y-3">
              <div className="relative overflow-hidden rounded-lg border border-slate-800 bg-black">
                <img className="w-full" src={apiClient.getV3ImagePreviewUrl(runId, selected.image_id)} alt={selected.image_id} />
                {overlay ? <Overlay image={selected} /> : null}
              </div>
              <Detail label="图片 ID（image_id）" value={selected.image_id} />
              <Detail label="本地绝对路径" value={selected.absolute_path || selected.path} />
              <Detail label="reject_reason" value={labelRejectReason(selected.reject_reason)} />
              <Detail label="capture_reason" value={String(selected.meta.capture_reason || "-")} />
              <Detail label="ui_state_hint" value={String(selected.meta.ui_state_hint || "-")} />
              <Detail label="duplicate_decision_reason" value={String(selected.duplicate_decision?.duplicate_decision_reason || "-")} />
              <Detail label="OCR 文本摘要" value={ocrSummary(selected)} />
              <Detail label="action_id" value={String(selected.meta.action_id || "-")} />
              <Detail label="candidate_region_type" value={labelRegionType(String(selected.meta.candidate_region_type || "unknown"))} />
              <div className="flex flex-wrap gap-2">
                <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void copyPath(selected.absolute_path || selected.path)}>
                  <Copy size={15} className="mr-1 inline" />
                  复制图片路径
                </button>
                <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void reveal(selected)}>
                  打开图片所在文件夹
                </button>
                <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${runId}/actions`}>
                  查看动作前后对比
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

function Overlay({ image }: { image: V3ImageRecord }) {
  const boxes = overlayBoxes(image);
  return (
    <>
      {boxes.map((box, index) => (
        <div
          key={`${box.kind}-${index}`}
          className={`pointer-events-none absolute border-2 ${boxClass(box.kind)}`}
          style={{ left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%` }}
          title={`${box.kind}: ${box.text || ""}`}
        />
      ))}
    </>
  );
}

function overlayBoxes(image: V3ImageRecord) {
  const rawBoxes = [image.meta.ocr_boxes, image.meta.showui_candidates, image.meta.fusion_candidates, image.meta.blocked_candidates].flat();
  const boxes: Array<{ kind: string; x: number; y: number; w: number; h: number; text?: string }> = [];
  for (const raw of rawBoxes) {
    if (!raw || typeof raw !== "object") continue;
    const item = raw as { bbox?: number[]; text?: string; label?: string; candidate_region_type?: string; blocked?: boolean };
    if (!Array.isArray(item.bbox) || item.bbox.length < 4) continue;
    const [x1, y1, x2, y2] = item.bbox;
    boxes.push({
      kind: item.blocked ? "blocked candidate" : item.candidate_region_type || "OCR bbox",
      x: Math.max(0, Math.min(100, x1 / 12)),
      y: Math.max(0, Math.min(100, y1 / 7)),
      w: Math.max(2, Math.min(100, (x2 - x1) / 12)),
      h: Math.max(2, Math.min(100, (y2 - y1) / 7)),
      text: item.text || item.label
    });
  }
  return boxes;
}

function boxClass(kind: string) {
  if (kind.includes("unsafe_chrome") || kind.includes("blocked")) return "border-red-400";
  if (kind.includes("ui_chrome") || kind.includes("fusion")) return "border-emerald-400";
  if (kind.includes("content_area")) return "border-amber-400";
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
