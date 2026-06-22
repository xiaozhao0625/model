import { Copy, FolderOpen, Maximize2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/layout/page-header";
import { Card } from "../components/ui/card";
import { apiClient } from "../lib/api-client";
import type { V3ImageRecord, V3RunRecord } from "../lib/api-types";
import { displayRunName, isDebugRun, labelRejectReason, labelStatus, overlayLabels } from "../lib/labels";

type Filter = "all" | "accepted" | "rejected" | "text" | "visual_fill" | "after_action" | "near_duplicate" | "cross_duplicate";
const filters: Array<[Filter, string]> = [["all", "全部"], ["accepted", "只看合格"], ["rejected", "只看拒绝"], ["text", "只看文字图"], ["visual_fill", "只看无文字补充图"], ["after_action", "只看动作后截图"], ["near_duplicate", "只看近似重复"], ["cross_duplicate", "只看跨轮重复"]];

export function V3GalleryRoute() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const collectionId = params.collectionId || searchParams.get("collection_id") || "";
  const [runs, setRuns] = useState<V3RunRecord[]>([]);
  const [runId, setRunId] = useState(params.runId || searchParams.get("run_id") || "");
  const [images, setImages] = useState<V3ImageRecord[]>([]);
  const [filter, setFilter] = useState<Filter>("accepted");
  const [selected, setSelected] = useState<V3ImageRecord | null>(null);
  const [message, setMessage] = useState("正在查找最近真实任务。");

  useEffect(() => {
    void load();
  }, [collectionId]);

  async function load() {
    try {
      if (collectionId) {
        const nextImages = await apiClient.getV3CollectionGallery(collectionId);
        setRuns([]);
        setRunId(String(nextImages[0]?.meta?.collection_run_id || ""));
        applyImages(nextImages);
        setMessage(`已加载最终有效图库：${nextImages.length} 张 accepted_unique。`);
        return;
      }
      const allRuns = await apiClient.listV3Runs();
      const realRuns = allRuns.filter((run) => !isDebugRun(run));
      setRuns(realRuns);
      const requested = params.runId || searchParams.get("run_id");
      if (requested) {
        await loadImages(requested);
        return;
      }
      const latest = realRuns[0];
      if (latest) await loadImages(latest.run_id);
      else setMessage("暂无真实任务。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function loadImages(nextRunId = runId) {
    if (!nextRunId) return;
    const nextImages = await apiClient.getV3Images(nextRunId);
    setRunId(nextRunId);
    applyImages(nextImages);
    setMessage(nextImages.length ? `已加载 ${nextImages.length} 张图片。` : "当前任务还没有图片。");
  }

  function applyImages(nextImages: V3ImageRecord[]) {
    setImages(nextImages);
    setSelected(nextImages.find((image) => image.bucket === "accepted") || nextImages[0] || null);
  }

  const filtered = useMemo(() => images.filter((image) => matchesFilter(image, filter)), [images, filter]);

  async function copyPath(path: string) {
    await navigator.clipboard?.writeText(path);
    setMessage(`已复制图片路径：${path}`);
  }

  async function reveal(image: V3ImageRecord) {
    const result = await apiClient.revealV3Image(imageRunId(image, runId), image.image_id);
    setMessage(`打开图片所在文件夹：${result.status} ${result.folder || result.path}`);
  }

  async function openRunFolder() {
    if (!runId) return;
    const result = await apiClient.openV3RunFolder(runId);
    setMessage(`打开任务文件夹：${result.status} ${result.path}`);
  }

  return (
    <div>
      <PageHeader title={collectionId ? "最终有效图库" : "结果图库"} description={collectionId ? "只展示 collection accepted_unique。跨轮重复图片不会进入最终交付图库。" : "查看合格图、拒绝图、OCR 文字框、候选框、动作后截图和本地图片路径。"} />
      <Card title={collectionId ? "最终交付图片与筛选" : "选择任务与筛选"}>
        <div className="flex flex-wrap items-center gap-2">
          {!collectionId ? (
            <select className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" value={runId} onChange={(event) => void loadImages(event.target.value)}>
              <option value="">选择任务</option>
              {runs.map((run) => <option key={run.run_id} value={run.run_id}>{displayRunName(run)} - {run.config.app_name}</option>)}
            </select>
          ) : null}
          {filters.map(([key, label]) => (
            <button key={key} className={`rounded-lg border px-3 py-2 text-sm ${filter === key ? "border-blue-500/50 bg-blue-500/10 text-blue-100" : "border-slate-700 text-slate-300"}`} onClick={() => setFilter(key)}>{label}</button>
          ))}
          {!collectionId ? <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void openRunFolder()}><FolderOpen size={15} className="mr-1 inline" />打开任务文件夹</button> : null}
        </div>
        <p className="mt-3 break-all text-sm text-slate-400">{message}</p>
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_440px]">
        <Card title={`图片列表：${filtered.length} 张`}>
          {filtered.length === 0 ? <p className="text-sm text-slate-500">当前筛选没有图片。</p> : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-4">
              {filtered.map((image) => (
                <button key={`${imageRunId(image, runId)}:${image.image_id}`} className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-left hover:border-blue-500/50" onClick={() => setSelected(image)}>
                  {image.file_exists === false ? <div className="grid aspect-video place-items-center rounded border border-slate-800 bg-slate-900 text-xs text-slate-500">文件不存在</div> : <img className="aspect-video w-full rounded border border-slate-800 object-cover" src={apiClient.getV3ImageThumbnailUrl(imageRunId(image, runId), image.image_id)} alt={image.image_id} />}
                  <p className="mt-2 truncate text-xs text-slate-300">{image.image_id}</p>
                  <p className="text-xs text-slate-500">分桶：{labelStatus(image.bucket)}</p>
                  <p className="text-xs text-slate-500">原因：{labelRejectReason(image.reject_reason)}</p>
                  <p className="text-xs text-slate-500">跨轮重复：{image.meta.duplicate_across_runs ? "是" : "否"}</p>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card title="图片详情" eyebrow={selected?.image_id || "未选择"}>
          {selected ? (
            <div className="space-y-3">
              {selected.file_exists === false ? <div className="grid aspect-video place-items-center rounded-lg border border-slate-800 bg-slate-950 text-sm text-slate-500">图片文件不存在</div> : <img className="w-full rounded-lg border border-slate-800" src={apiClient.getV3ImagePreviewUrl(imageRunId(selected, runId), selected.image_id)} alt={selected.image_id} />}
              <Detail label="合格 / 拒绝" value={labelStatus(selected.bucket)} />
              <Detail label="原因" value={labelRejectReason(selected.reject_reason)} />
              <Detail label="来源 run_id" value={imageRunId(selected, runId)} />
              <Detail label="是否文字图" value={isTextImage(selected) ? "是" : "否"} />
              <Detail label="是否无文字补充图" value={isVisualFill(selected) ? "是" : "否"} />
              <Detail label="是否跨轮重复" value={selected.meta.duplicate_across_runs ? "是" : "否"} />
              <Detail label="OCR 文本摘要" value={ocrSummary(selected)} />
              <Detail label="本地路径" value={selected.absolute_path || selected.path} />
              <details className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <summary className="cursor-pointer text-xs text-slate-400">高级调试信息：OCR / ShowUI / 融合候选</summary>
                <p className="mt-2 text-xs text-slate-500">{Object.values(overlayLabels).join(" / ")}</p>
                <pre className="mt-2 max-h-60 overflow-auto text-xs text-slate-500">{JSON.stringify(selected.meta, null, 2)}</pre>
              </details>
              <div className="flex flex-wrap gap-2">
                <button className="rounded-lg border border-blue-500/40 px-3 py-2 text-sm text-blue-100" onClick={() => void copyPath(selected.absolute_path || selected.path)}><Copy size={15} className="mr-1 inline" />复制图片路径</button>
                <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" onClick={() => void reveal(selected)}><FolderOpen size={15} className="mr-1 inline" />打开图片文件夹</button>
                <Link className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200" to={`/v3/runs/${imageRunId(selected, runId)}/actions`}><Maximize2 size={15} className="mr-1 inline" />查看运行审计</Link>
              </div>
            </div>
          ) : <p className="text-sm text-slate-500">当前没有选中图片。</p>}
        </Card>
      </div>
    </div>
  );
}

function matchesFilter(image: V3ImageRecord, filter: Filter) {
  if (filter === "all") return true;
  if (filter === "accepted" || filter === "rejected") return image.bucket === filter;
  if (filter === "text") return isTextImage(image);
  if (filter === "visual_fill") return isVisualFill(image);
  if (filter === "after_action") return image.meta.capture_reason === "after_action";
  if (filter === "near_duplicate") return image.near_duplicate || image.reject_reason === "near_duplicate";
  if (filter === "cross_duplicate") return image.meta.duplicate_across_runs === true || image.reject_reason === "rejected_duplicate_across_runs";
  return true;
}

function imageRunId(image: V3ImageRecord, fallback: string) {
  return String(image.meta.collection_run_id || image.meta.source_run_id || fallback);
}

function isTextImage(image: V3ImageRecord) {
  return ["accepted_text_ui", "accepted_text_hud"].includes(String(image.meta.accepted_class || ""));
}

function isVisualFill(image: V3ImageRecord) {
  return image.meta.accepted_class === "accepted_visual_fill";
}

function ocrSummary(image: V3ImageRecord) {
  const ocr = image.meta.ocr as { text_boxes?: Array<{ text?: string }> } | undefined;
  const text = ocr?.text_boxes?.map((box) => box.text).filter(Boolean).join(" / ");
  return text || "-";
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="break-all text-sm text-slate-200">{value}</p>
    </div>
  );
}
