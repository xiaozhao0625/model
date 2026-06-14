import { Copy, Download, ExternalLink, FolderOpen, ImageOff, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../../lib/api-client";
import type { ArtifactSampleRecord, RunArtifactRecord } from "../../lib/api-types";
import { Badge } from "../ui/badge";
import { Card } from "../ui/card";

const buckets = ["fixed", "low", "high", "rejected", "duplicates"];
const bucketText: Record<string, string> = {
  fixed: "修复",
  low: "低质",
  high: "高质",
  rejected: "拒绝",
  duplicates: "重复"
};

export function RunArtifactInspector({ runId }: { runId: string }) {
  const [artifact, setArtifact] = useState<RunArtifactRecord | null>(null);
  const [samples, setSamples] = useState<ArtifactSampleRecord[]>([]);
  const [bucket, setBucket] = useState("low");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void loadArtifacts();
  }, [runId]);

  useEffect(() => {
    if (artifact) {
      setSamples(samplesForBucket(artifact, bucket));
    }
  }, [artifact, bucket]);

  const thumbnailRoot = useMemo(() => apiClient.getBaseUrl(), []);

  async function loadArtifacts() {
    setLoading(true);
    setError("");
    try {
      const record = await apiClient.getRunArtifacts(runId);
      setArtifact(record);
      setSamples(samplesForBucket(record, bucket));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function copyPath() {
    if (!artifact) {
      return;
    }
    await navigator.clipboard.writeText(artifact.artifact_root);
    setMessage("产物路径已复制。");
  }

  async function openFolder() {
    const result = await apiClient.openRunArtifactFolder(runId, bucket === "duplicates" ? {} : { bucket });
    setMessage(result.desktop_session_required ? "需要 Worker 桌面会话。" : `打开文件夹：${result.status}`);
  }

  async function packageSample() {
    const result = await apiClient.packageRunArtifactSample(runId, { buckets: ["fixed", "low", "high", "rejected"], limit_per_bucket: 20 });
    setMessage(`样本打包：${result.status}${result.file_count ? `（${result.file_count} 个文件）` : ""}`);
  }

  return (
    <Card title="截图产物检查器" eyebrow="受控 Worker 产物">
      {loading ? <p className="text-sm text-slate-400">正在加载产物元数据...</p> : null}
      {error ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-100">
          <p>{error}</p>
          <button className="mt-3 inline-flex min-h-9 items-center gap-2 rounded-lg border border-red-400/40 px-3 py-2 text-sm" onClick={() => void loadArtifacts()}>
            <RefreshCw size={16} />
            重试
          </button>
        </div>
      ) : null}
      {artifact ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <Info label="任务 ID" value={artifact.run_id} mono />
            <Info label="Worker" value={artifact.worker_id} mono />
            <Info label="角色" value={artifact.worker_role} />
            <Info label="状态" value={artifact.status} />
            <Info label="产物根目录" value={artifact.artifact_root} mono wide />
            <Info label="有效截图" value={String(artifact.summary.valid_total ?? 0)} />
            <Info label="重复截图" value={String(artifact.bucket_counts.duplicates ?? 0)} />
            <Info label="summary/meta" value={`${artifact.has_summary_json ? "有 summary" : "无 summary"} / ${artifact.has_meta_jsonl ? "有 meta" : "无 meta"}`} />
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" onClick={() => void copyPath()} title="复制 Worker 产物路径">
              <Copy size={16} />
              复制路径
            </button>
            <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" onClick={() => void openFolder()} title="在 Worker 桌面打开文件夹">
              <FolderOpen size={16} />
              打开 Worker 文件夹
            </button>
            <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" onClick={() => void packageSample()} title="在 Worker 上创建受限样本包">
              <Download size={16} />
              打包样本
            </button>
            <a className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" href={`${thumbnailRoot}/api/runs/${encodeURIComponent(runId)}/artifact-actions/download-sample`} title="下载受限样本包">
              <Download size={16} />
              下载样本
            </a>
          </div>
          {message ? <p className="text-xs text-slate-400">{message}</p> : null}
          <div className="flex flex-wrap gap-2">
            {buckets.map((item) => (
              <button
                key={item}
                className={`min-h-9 rounded-lg border px-3 py-2 text-sm ${bucket === item ? "border-blue-400 bg-blue-500/15 text-blue-100" : "border-slate-800 bg-slate-950 text-slate-300"}`}
                onClick={() => setBucket(item)}
              >
                {bucketText[item] || item} <span className="font-mono text-xs text-slate-500">{artifact.bucket_counts[item] ?? 0}</span>
              </button>
            ))}
          </div>
          {samples.length === 0 ? (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">当前分桶没有样本。</div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {samples.map((sample) => (
                <SampleCard key={sample.file_id} sample={sample} runId={runId} thumbnailRoot={thumbnailRoot} />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </Card>
  );
}

function samplesForBucket(artifact: RunArtifactRecord, bucket: string): ArtifactSampleRecord[] {
  return artifact.sample_files.filter((sample) => sample.bucket === bucket).slice(0, 20);
}

function Info({ label, value, mono = false, wide = false }: { label: string; value: string; mono?: boolean; wide?: boolean }) {
  return (
    <div className={`rounded-lg border border-slate-800 bg-slate-950 p-3 ${wide ? "md:col-span-2" : ""}`}>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`mt-1 break-all text-sm text-slate-200 ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

function SampleCard({ sample, runId, thumbnailRoot }: { sample: ArtifactSampleRecord; runId: string; thumbnailRoot: string }) {
  const [failed, setFailed] = useState(false);
  const thumbnailUrl = `${thumbnailRoot}/api/runs/${encodeURIComponent(runId)}/artifacts/thumbnail?file_id=${encodeURIComponent(sample.file_id)}`;
  return (
    <article className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
      <div className="flex aspect-video items-center justify-center bg-slate-900">
        {failed ? (
          <div className="flex flex-col items-center gap-2 text-slate-500">
            <ImageOff size={22} />
            <span className="text-xs">缩略图不可用</span>
          </div>
        ) : (
          <img src={thumbnailUrl} alt={sample.file_name} className="h-full w-full object-contain" loading="lazy" onError={() => setFailed(true)} />
        )}
      </div>
      <div className="space-y-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <p className="break-all font-mono text-xs text-blue-200">{sample.file_name}</p>
          <a href={thumbnailUrl} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-100" title="打开缩略图">
            <ExternalLink size={15} />
          </a>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge className="border-slate-700 bg-slate-900 text-slate-200">{bucketText[sample.bucket] || sample.bucket}</Badge>
          <Badge className="border-slate-700 bg-slate-900 text-slate-200">{captureLabel(sample)}</Badge>
          <Badge className="border-slate-700 bg-slate-900 text-slate-200">输出 {sample.output_resolution || `${sample.width}x${sample.height}`}</Badge>
          {sample.test_source ? <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">测试源</Badge> : null}
          {sample.content_only ? <Badge className="border-blue-500/40 bg-blue-500/10 text-blue-100">网页内容区</Badge> : null}
          {sample.is_duplicate ? <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">重复</Badge> : null}
          {sample.rejected_reason ? <Badge className="border-red-500/40 bg-red-500/10 text-red-100">{sample.rejected_reason}</Badge> : null}
        </div>
        <p className="break-all font-mono text-[11px] text-slate-500">{sample.safe_display_path}</p>
        <dl className="grid gap-1 text-[11px] text-slate-500">
          <MetaLine label="capture_method" value={sample.capture_method} />
          <MetaLine label="来源说明" value={sourceDescription(sample)} />
          <MetaLine label="source_resolution" value={sample.source_resolution || "unknown"} />
          <MetaLine label="output_resolution" value={sample.output_resolution || `${sample.width}x${sample.height}`} />
          <MetaLine label="test_source" value={String(sample.test_source ?? false)} />
          <MetaLine label="production_capture" value={String(sample.production_capture ?? !sample.test_source)} />
          {sample.content_only !== undefined ? <MetaLine label="content_only" value={String(sample.content_only)} /> : null}
          {sample.browser_chrome_included !== undefined ? <MetaLine label="browser_chrome_included" value={String(sample.browser_chrome_included)} /> : null}
          {sample.taskbar_included !== undefined ? <MetaLine label="taskbar_included" value={String(sample.taskbar_included)} /> : null}
        </dl>
      </div>
    </article>
  );
}

function MetaLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-2">
      <dt className="font-mono text-slate-600">{label}</dt>
      <dd className="break-all font-mono text-slate-400">{value}</dd>
    </div>
  );
}

function captureLabel(sample: ArtifactSampleRecord): string {
  if (sample.capture_method === "ffmpeg_testsrc") {
    return "测试源";
  }
  if (sample.capture_method === "playwright_edge_content_only") {
    return "网页内容区";
  }
  if (sample.capture_method === "obs_or_ffmpeg" || sample.source_type?.includes("game")) {
    return "OBS/游戏源";
  }
  if (sample.capture_method === "windows_safe_window_capture") {
    return "安全窗口";
  }
  if (sample.capture_method === "adb_screencap") {
    return "Android 设备屏幕";
  }
  return sample.capture_method;
}

function sourceDescription(sample: ArtifactSampleRecord): string {
  if (sample.capture_method === "ffmpeg_testsrc") {
    return "ffmpeg testsrc 链路 smoke，不代表正式游戏采集尺寸";
  }
  if (sample.capture_method === "playwright_edge_content_only") {
    return "Playwright 视口/页面内容区；不包含浏览器外壳和任务栏";
  }
  if (sample.capture_method === "obs_or_ffmpeg" || sample.source_type?.includes("game")) {
    return "OBS canvas、source 或游戏窗口有效画面";
  }
  if (sample.capture_method === "windows_safe_window_capture") {
    return "记事本/计算器/资源管理器等本地安全测试窗口；不包含任务栏";
  }
  if (sample.capture_method === "adb_screencap") {
    return "ADB screencap 设备屏幕分辨率";
  }
  return sample.source_type || "采集来源";
}
