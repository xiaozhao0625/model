import { Copy, Download, ExternalLink, FolderOpen, ImageOff, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../../lib/api-client";
import type { ArtifactSampleRecord, RunArtifactRecord } from "../../lib/api-types";
import { Badge } from "../ui/badge";
import { Card } from "../ui/card";

const buckets = ["fixed", "low", "high", "rejected", "duplicates"];

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
    setMessage("Artifact path copied.");
  }

  async function openFolder() {
    const result = await apiClient.openRunArtifactFolder(runId, bucket === "duplicates" ? {} : { bucket });
    setMessage(result.desktop_session_required ? "Worker desktop session required." : `Open folder: ${result.status}`);
  }

  async function packageSample() {
    const result = await apiClient.packageRunArtifactSample(runId, { buckets: ["fixed", "low", "high", "rejected"], limit_per_bucket: 20 });
    setMessage(`Sample package: ${result.status}${result.file_count ? ` (${result.file_count} files)` : ""}`);
  }

  return (
    <Card title="Run Artifact Inspector" eyebrow="controlled Worker artifacts">
      {loading ? <p className="text-sm text-slate-400">Loading artifact metadata...</p> : null}
      {error ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-100">
          <p>{error}</p>
          <button className="mt-3 inline-flex min-h-9 items-center gap-2 rounded-lg border border-red-400/40 px-3 py-2 text-sm" onClick={() => void loadArtifacts()}>
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      ) : null}
      {artifact ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <Info label="run_id" value={artifact.run_id} mono />
            <Info label="worker" value={artifact.worker_id} mono />
            <Info label="role" value={artifact.worker_role} />
            <Info label="status" value={artifact.status} />
            <Info label="artifact root" value={artifact.artifact_root} mono wide />
            <Info label="valid_total" value={String(artifact.summary.valid_total ?? 0)} />
            <Info label="duplicates" value={String(artifact.bucket_counts.duplicates ?? 0)} />
            <Info label="summary/meta" value={`${artifact.has_summary_json ? "summary" : "no summary"} / ${artifact.has_meta_jsonl ? "meta" : "no meta"}`} />
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" onClick={() => void copyPath()} title="Copy Worker artifact path">
              <Copy size={16} />
              Copy path
            </button>
            <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" onClick={() => void openFolder()} title="Open folder on the Worker desktop">
              <FolderOpen size={16} />
              Open Worker folder
            </button>
            <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" onClick={() => void packageSample()} title="Create a limited sample zip on the Worker">
              <Download size={16} />
              Package sample
            </button>
            <a className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 hover:border-slate-500" href={`${thumbnailRoot}/api/runs/${encodeURIComponent(runId)}/artifact-actions/download-sample`} title="Download the limited sample zip">
              <Download size={16} />
              Download sample
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
                {item} <span className="font-mono text-xs text-slate-500">{artifact.bucket_counts[item] ?? 0}</span>
              </button>
            ))}
          </div>
          {samples.length === 0 ? (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">No samples in this bucket.</div>
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
            <span className="text-xs">thumbnail unavailable</span>
          </div>
        ) : (
          <img src={thumbnailUrl} alt={sample.file_name} className="h-full w-full object-contain" loading="lazy" onError={() => setFailed(true)} />
        )}
      </div>
      <div className="space-y-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <p className="break-all font-mono text-xs text-blue-200">{sample.file_name}</p>
          <a href={thumbnailUrl} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-100" title="Open thumbnail">
            <ExternalLink size={15} />
          </a>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge className="border-slate-700 bg-slate-900 text-slate-200">{sample.bucket}</Badge>
          <Badge className="border-slate-700 bg-slate-900 text-slate-200">{captureLabel(sample)}</Badge>
          <Badge className="border-slate-700 bg-slate-900 text-slate-200">output {sample.output_resolution || `${sample.width}x${sample.height}`}</Badge>
          {sample.test_source ? <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">test source</Badge> : null}
          {sample.content_only ? <Badge className="border-blue-500/40 bg-blue-500/10 text-blue-100">content-only</Badge> : null}
          {sample.is_duplicate ? <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">duplicate</Badge> : null}
          {sample.rejected_reason ? <Badge className="border-red-500/40 bg-red-500/10 text-red-100">{sample.rejected_reason}</Badge> : null}
        </div>
        <p className="break-all font-mono text-[11px] text-slate-500">{sample.safe_display_path}</p>
        <dl className="grid gap-1 text-[11px] text-slate-500">
          <MetaLine label="capture_method" value={sample.capture_method} />
          <MetaLine label="source" value={sourceDescription(sample)} />
          <MetaLine label="source_resolution" value={sample.source_resolution || "unknown"} />
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
    <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-2">
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
  if (sample.capture_method === "adb_screencap") {
    return "Android 设备屏幕";
  }
  return sample.capture_method;
}

function sourceDescription(sample: ArtifactSampleRecord): string {
  if (sample.capture_method === "ffmpeg_testsrc") {
    return "ffmpeg testsrc smoke only, not production game capture";
  }
  if (sample.capture_method === "playwright_edge_content_only") {
    return "Playwright viewport/page content area; browser chrome and taskbar excluded";
  }
  if (sample.capture_method === "adb_screencap") {
    return "ADB screencap device screen resolution";
  }
  return sample.source_type || "capture source";
}
